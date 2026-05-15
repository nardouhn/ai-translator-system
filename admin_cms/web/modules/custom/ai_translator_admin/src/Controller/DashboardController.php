<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\ai_translator_admin\Services\FastApiClient;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Renders the AI Translator Admin dashboard.
 *
 * Fetches live statistics from the FastAPI backend (/api/admin/stats) and
 * displays them as a styled 5-card stat grid using a render array with
 * attached inline CSS — no external theme template required.
 */
class DashboardController extends ControllerBase {

  /**
   * The FastAPI client service.
   *
   * @var \Drupal\ai_translator_admin\Services\FastApiClient
   */
  protected FastApiClient $apiClient;

  /**
   * Constructs a DashboardController object.
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
   * Builds and returns the dashboard render array.
   *
   * Fetches /api/admin/stats from the FastAPI backend. If the request
   * fails (NULL response or non-200 status), graceful fallback values (0)
   * are displayed and a Drupal messenger error is shown.
   *
   * @return array
   *   A Drupal render array.
   */
  public function build(): array {
    // -------------------------------------------------------------------------
    // 1. Default / fallback values — all five metrics.
    // -------------------------------------------------------------------------
    $stats = [
      'total_texts_translated'   => 0,
      'total_files_translated'   => 0,
      'total_data_processed_mb'  => 0.0,
      'total_sessions'           => 0,
      'error_rate_percent'       => 0.0,
    ];
    $fetch_error = FALSE;

    // -------------------------------------------------------------------------
    // 2. Call FastAPI backend.
    //    FastApiClient::request() reads base_url & api_key from module config
    //    and injects "Authorization: Bearer <key>" automatically.
    // -------------------------------------------------------------------------
    $response = $this->apiClient->request('GET', '/api/admin/stats');

    if ($response === NULL) {
      $fetch_error = TRUE;
      $this->messenger()->addError(
        $this->t('Could not reach the FastAPI backend. Displaying default values.')
      );
    }
    elseif ($response->getStatusCode() !== 200) {
      $fetch_error = TRUE;
      $this->messenger()->addError(
        $this->t('FastAPI returned an unexpected status: @code.', [
          '@code' => $response->getStatusCode(),
        ])
      );
    }
    else {
      $body    = (string) $response->getBody();
      $decoded = json_decode($body, TRUE);

      if (is_array($decoded)) {
        $stats['total_texts_translated']  = (int)   ($decoded['total_texts_translated']  ?? 0);
        $stats['total_files_translated']  = (int)   ($decoded['total_files_translated']  ?? 0);
        $stats['total_data_processed_mb'] = (float) ($decoded['total_data_processed_mb'] ?? 0.0);
        $stats['total_sessions']          = (int)   ($decoded['total_sessions']           ?? 0);
        $stats['error_rate_percent']      = (float) ($decoded['error_rate_percent']       ?? 0.0);
      }
    }

    // -------------------------------------------------------------------------
    // 3. Format numbers for display.
    // -------------------------------------------------------------------------
    $fmt_texts    = number_format($stats['total_texts_translated']);
    $fmt_files    = number_format($stats['total_files_translated']);
    $fmt_mb       = number_format($stats['total_data_processed_mb'], 2) . ' MB';
    $fmt_sessions = number_format($stats['total_sessions']);
    $fmt_error    = number_format($stats['error_rate_percent'], 2) . '%';

    // -------------------------------------------------------------------------
    // 4. Build the render array.
    // -------------------------------------------------------------------------
    $build = [];

    // Inline stylesheet — scoped to .ai-dashboard so it does not leak.
    $build['#attached']['html_head'][] = [
      [
        '#tag'        => 'style',
        '#value'      => $this->getInlineCss(),
        '#attributes' => ['id' => 'ai-translator-dashboard-css'],
      ],
      'ai_translator_admin_dashboard_css',
    ];

    // Page wrapper.
    $build['dashboard'] = [
      '#type'       => 'container',
      '#attributes' => ['class' => ['ai-dashboard']],
    ];

    // Hero header.
    $build['dashboard']['header'] = [
      '#markup' => '<div class="ai-dashboard__header">
        <div class="ai-dashboard__icon">🤖</div>
        <div>
          <h2 class="ai-dashboard__title">AI Translator — Live Dashboard</h2>
          <p class="ai-dashboard__subtitle">Real-time statistics fetched from the FastAPI backend</p>
        </div>
      </div>',
    ];

    // Error banner (only when the backend call failed).
    if ($fetch_error) {
      $build['dashboard']['error_banner'] = [
        '#markup' => '<div class="ai-dashboard__error-banner">
          ⚠️ &nbsp;Backend unreachable — statistics may be stale or zero.
        </div>',
      ];
    }

    // 5-card stat grid.
    $build['dashboard']['stats_grid'] = [
      '#markup' => '<div class="ai-dashboard__grid">'
        . $this->renderStatCard('📝', 'Texts Translated', $fmt_texts,    'texts')
        . $this->renderStatCard('📁', 'Files Translated',  $fmt_files,    'files')
        . $this->renderStatCard('💾', 'Data Processed',    $fmt_mb,       'data')
        . $this->renderStatCard('👥', 'Total Sessions',    $fmt_sessions, 'sessions')
        . $this->renderStatCard('⚠️', 'Error Rate',        $fmt_error,    'errors')
        . '</div>',
    ];

    // Quick-action links.
    $build['dashboard']['actions'] = [
      '#markup' => '<div class="ai-dashboard__actions">
        <a class="ai-dashboard__action-btn ai-dashboard__action-btn--danger"
           href="/admin/config/ai-translator/clear-cache">
          🗑️ &nbsp;Clear Redis Cache
        </a>
        <a class="ai-dashboard__action-btn"
           href="/admin/config/ai-translator/settings">
          ⚙️ &nbsp;Module Settings
        </a>
      </div>',
    ];

    return $build;
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /**
   * Returns an HTML string for a single statistic card.
   *
   * @param string $icon
   *   An emoji icon.
   * @param string $label
   *   The human-readable metric label.
   * @param string $value
   *   The formatted value to display prominently (already includes unit if any).
   * @param string $modifier
   *   A BEM modifier class appended to the card element (texts|files|data|sessions|errors).
   *
   * @return string
   *   HTML markup for the card.
   */
  private function renderStatCard(string $icon, string $label, string $value, string $modifier): string {
    return sprintf(
      '<div class="ai-dashboard__card ai-dashboard__card--%s">
        <div class="ai-dashboard__card-icon">%s</div>
        <div class="ai-dashboard__card-value">%s</div>
        <div class="ai-dashboard__card-label">%s</div>
      </div>',
      htmlspecialchars($modifier, ENT_QUOTES, 'UTF-8'),
      $icon,
      htmlspecialchars($value, ENT_QUOTES, 'UTF-8'),
      htmlspecialchars($label, ENT_QUOTES, 'UTF-8')
    );
  }

  /**
   * Returns the scoped inline CSS for the dashboard.
   *
   * Inline CSS keeps the dashboard self-contained across different Drupal
   * admin themes (Claro, Gin, Seven, etc.).
   *
   * Color palette per card modifier:
   *   --texts    : Indigo  #7c3aed
   *   --files    : Blue    #0284c7
   *   --data     : Green   #16a34a
   *   --sessions : Amber   #d97706
   *   --errors   : Red     #dc2626
   *
   * @return string
   *   Raw CSS text.
   */
  private function getInlineCss(): string {
    return <<<CSS
/* ── AI Translator Admin Dashboard ─────────────────────────────────────── */
.ai-dashboard {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  max-width: 1000px;
  padding: 0 0 2rem;
}

/* Header */
.ai-dashboard__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  color: #f1f5f9;
  border-radius: 12px;
  padding: 1.5rem 2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 24px rgba(0,0,0,.25);
}
.ai-dashboard__icon {
  font-size: 2.8rem;
  line-height: 1;
}
.ai-dashboard__title {
  margin: 0 0 .25rem;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -.3px;
}
.ai-dashboard__subtitle {
  margin: 0;
  font-size: .85rem;
  color: #94a3b8;
}

/* Error banner */
.ai-dashboard__error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 8px;
  padding: .85rem 1.25rem;
  margin-bottom: 1.25rem;
  font-size: .9rem;
  font-weight: 500;
}

/* Stat card grid — 5 cards, responsive */
.ai-dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}

.ai-dashboard__card {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.75rem 1.25rem;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  border-top: 4px solid transparent;
  transition: transform .15s ease, box-shadow .15s ease;
}
.ai-dashboard__card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,.13);
}

/* Per-card accent colours */
.ai-dashboard__card--texts    { border-top-color: #7c3aed; }  /* Indigo — Text */
.ai-dashboard__card--files    { border-top-color: #0284c7; }  /* Blue   — File */
.ai-dashboard__card--data     { border-top-color: #16a34a; }  /* Green  — MB   */
.ai-dashboard__card--sessions { border-top-color: #d97706; }  /* Amber  — Sessions */
.ai-dashboard__card--errors   { border-top-color: #dc2626; }  /* Red    — Error rate */

.ai-dashboard__card-icon {
  font-size: 2.25rem;
  margin-bottom: .5rem;
  line-height: 1;
}
.ai-dashboard__card-value {
  font-size: 2.1rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -1px;
  line-height: 1.1;
}
.ai-dashboard__card-label {
  margin-top: .4rem;
  font-size: .78rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .5px;
}

/* Action buttons */
.ai-dashboard__actions {
  display: flex;
  gap: .75rem;
  flex-wrap: wrap;
}
.ai-dashboard__action-btn {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  padding: .65rem 1.25rem;
  border-radius: 8px;
  font-size: .875rem;
  font-weight: 600;
  text-decoration: none;
  background: #f1f5f9;
  color: #1e293b;
  border: 1px solid #e2e8f0;
  transition: background .15s, box-shadow .15s;
}
.ai-dashboard__action-btn:hover {
  background: #e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
}
.ai-dashboard__action-btn--danger {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}
.ai-dashboard__action-btn--danger:hover {
  background: #fee2e2;
}
CSS;
  }

}
