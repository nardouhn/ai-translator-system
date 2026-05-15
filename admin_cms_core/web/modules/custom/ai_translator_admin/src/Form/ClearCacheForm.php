<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Form;

use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\ai_translator_admin\Services\FastApiClient;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides a form to clear the Upstash Redis cache on the FastAPI backend.
 *
 * Submitting the form POSTs to /api/admin/clear-cache via the shared
 * FastApiClient service. Success and failure are both surfaced through
 * Drupal's messenger service so they appear as standard status messages.
 *
 * This form intentionally extends FormBase (not ConfigFormBase) because
 * no Drupal configuration is read or saved — the action is fully remote.
 */
class ClearCacheForm extends FormBase {

  /**
   * The FastAPI client service.
   *
   * @var \Drupal\ai_translator_admin\Services\FastApiClient
   */
  protected FastApiClient $apiClient;

  /**
   * Constructs a ClearCacheForm object.
   *
   * @param \Drupal\ai_translator_admin\Services\FastApiClient $api_client
   *   The custom FastAPI client service.
   */
  public function __construct(FastApiClient $api_client) {
    $this->apiClient = $api_client;
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container): static {
    return new static(
      $container->get('ai_translator_admin.api_client')
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'ai_translator_admin_clear_cache_form';
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state): array {
    $form['#attributes']['class'][] = 'ai-clear-cache-form';

    // Inline CSS — keeps the form styled independently of the admin theme.
    $form['#attached']['html_head'][] = [
      [
        '#tag'        => 'style',
        '#value'      => $this->getInlineCss(),
        '#attributes' => ['id' => 'ai-translator-cache-form-css'],
      ],
      'ai_translator_admin_cache_form_css',
    ];

    // ── Info card ───────────────────────────────────────────────────────────
    $form['info'] = [
      '#markup' => '<div class="ai-cache-form__info-card">
        <div class="ai-cache-form__info-icon">⚡</div>
        <div>
          <strong>Upstash Redis Cache</strong>
          <p>Clearing the cache will invalidate all cached translation results stored
             in Upstash Redis. In-progress jobs are not affected. This action cannot
             be undone.</p>
        </div>
      </div>',
    ];

    // ── Submit ───────────────────────────────────────────────────────────────
    $form['actions'] = [
      '#type' => 'actions',
    ];

    $form['actions']['submit'] = [
      '#type'        => 'submit',
      '#value'       => $this->t('🗑️  Clear Upstash Redis Cache'),
      '#button_type' => 'danger',
      '#attributes'  => [
        'class'   => ['ai-cache-form__submit-btn'],
        // Require explicit confirmation via the browser's built-in dialog.
        'onclick' => "return confirm('Are you sure you want to clear the entire Redis cache? This cannot be undone.');",
      ],
    ];

    $form['actions']['back'] = [
      '#markup' => '<a class="ai-cache-form__back-link" href="/admin/config/ai-translator/dashboard">
        ← Back to Dashboard
      </a>',
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   *
   * POSTs to the FastAPI /api/admin/clear-cache endpoint. Adds a Drupal
   * status message on success or an error message on failure. HTTP 2xx
   * status codes are all treated as success.
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    $response = $this->apiClient->request('POST', '/api/admin/clear-cache');

    if ($response === NULL) {
      // FastApiClient already logged the Guzzle exception; surface it to the UI.
      $this->messenger()->addError(
        $this->t('Could not connect to the FastAPI backend. The cache was <strong>not</strong> cleared. Please check the connection settings and try again.')
      );
      return;
    }

    $status_code = $response->getStatusCode();

    // Treat any 2xx response as success.
    if ($status_code >= 200 && $status_code < 300) {
      // Optionally parse a message from the JSON body.
      $body    = (string) $response->getBody();
      $decoded = json_decode($body, TRUE);
      $detail  = $decoded['detail'] ?? $decoded['message'] ?? NULL;

      $success_msg = $detail
        ? $this->t('Redis cache cleared successfully. Backend said: "@detail"', ['@detail' => $detail])
        : $this->t('Upstash Redis cache cleared successfully.');

      $this->messenger()->addStatus($success_msg);
    }
    else {
      $this->messenger()->addError(
        $this->t(
          'The FastAPI backend returned an unexpected response (HTTP @code). The cache may not have been cleared.',
          ['@code' => $status_code]
        )
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * Returns the scoped inline CSS for the clear-cache form.
   *
   * @return string
   *   Raw CSS text.
   */
  private function getInlineCss(): string {
    return <<<CSS
/* ── AI Translator Admin — Clear Cache Form ────────────────────────────── */
.ai-clear-cache-form {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  max-width: 620px;
}

.ai-cache-form__info-card {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 4px solid #f59e0b;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
  color: #78350f;
  font-size: .9rem;
  line-height: 1.55;
}
.ai-cache-form__info-icon {
  font-size: 1.8rem;
  line-height: 1;
  flex-shrink: 0;
  margin-top: .1rem;
}
.ai-cache-form__info-card strong {
  display: block;
  font-size: 1rem;
  margin-bottom: .3rem;
  color: #92400e;
}
.ai-cache-form__info-card p {
  margin: 0;
}

/* Submit button override — Claro/Gin use their own button styles, so we
   layer on top without !important where possible. */
.ai-cache-form__submit-btn,
input.ai-cache-form__submit-btn {
  background: #dc2626;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: .7rem 1.5rem;
  font-size: .9rem;
  font-weight: 700;
  cursor: pointer;
  transition: background .15s, box-shadow .15s;
}
.ai-cache-form__submit-btn:hover,
input.ai-cache-form__submit-btn:hover {
  background: #b91c1c;
  box-shadow: 0 3px 10px rgba(220,38,38,.35);
}

.ai-cache-form__back-link {
  display: inline-flex;
  align-items: center;
  margin-left: .75rem;
  font-size: .875rem;
  color: #475569;
  text-decoration: none;
  font-weight: 500;
}
.ai-cache-form__back-link:hover {
  color: #1e293b;
  text-decoration: underline;
}
CSS;
  }

}
