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
 * displays them as a styled stat card grid using a render array with
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
   * fails (NULL response or non-200 status), graceful fallback values are
   * displayed and an error message is shown in the Drupal messenger.
   *
   * @return array
   *   A Drupal render array.
   */
  public function build(): array {
    // --------------------------------------------------------------------------
    // 1. Fetch stats from the FastAPI backend.
    // --------------------------------------------------------------------------
    $stats = [
      'total_tokens' => 0,
      'total_files'  => 0,
    ];
    $fetch_error = FALSE;

    $response = $this->apiClient->request('GET', '/api/admin/stats');

    if ($response === NULL) {
      $fetch_error = TRUE;
      $this->messenger()->addError(
        $this->t('Could not reach the FastAPI backend. Displaying last known or default values.')
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
      $body = (string) $response->getBody();
      $decoded = json_decode($body, TRUE);
      if (is_array($decoded)) {
        $stats['total_tokens'] = (int) ($decoded['total_tokens'] ?? 0);
        $stats['total_files']  = (int) ($decoded['total_files'] ?? 0);
      }
    }

    // --------------------------------------------------------------------------
    // 2. Format numbers for display.
    // --------------------------------------------------------------------------
    $formatted_tokens = number_format($stats['total_tokens']);
    $formatted_files  = number_format($stats['total_files']);

    // --------------------------------------------------------------------------
    // 3. Build the render array.
    //    Inline CSS keeps this self-contained without a .libraries.yml entry.
    // --------------------------------------------------------------------------
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

    // Stat card grid.
    $build['dashboard']['stats_grid'] = [
      '#markup' => '<div class="ai-dashboard__grid">'
        . $this->renderStatCard('🗂️', 'Total Files Translated', $formatted_files, 'files')
        . $this->renderStatCard('🔤', 'Total Tokens Consumed', $formatted_tokens, 'tokens')
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
   *   An emoji or short icon string.
   * @param string $label
   *   The human-readable metric label.
   * @param string $value
   *   The formatted value to display prominently.
   * @param string $modifier
   *   A BEM modifier class appended to the card element.
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
   * Using inline CSS ensures the dashboard looks correct regardless of the
   * active Drupal admin theme (Claro, Gin, Seven, etc.).
   *
   * @return string
   *   Raw CSS text.
   */
  private function getInlineCss(): string {
    return <<<CSS
/* ── AI Translator Admin Dashboard ─────────────────────────────────────── */
.ai-dashboard {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  max-width: 900px;
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

/* Stat card grid */
.ai-dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}

.ai-dashboard__card {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.75rem 1.5rem;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  border-top: 4px solid transparent;
  transition: transform .15s ease, box-shadow .15s ease;
}
.ai-dashboard__card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,.13);
}
.ai-dashboard__card--files  { border-top-color: #6366f1; }
.ai-dashboard__card--tokens { border-top-color: #0ea5e9; }

.ai-dashboard__card-icon {
  font-size: 2.25rem;
  margin-bottom: .5rem;
  line-height: 1;
}
.ai-dashboard__card-value {
  font-size: 2.4rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -1px;
  line-height: 1.1;
}
.ai-dashboard__card-label {
  margin-top: .4rem;
  font-size: .8rem;
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
