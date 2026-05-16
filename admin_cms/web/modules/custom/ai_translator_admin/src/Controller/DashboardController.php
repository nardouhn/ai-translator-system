<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Controller;

use Drupal\Core\Controller\ControllerBase;

/**
 * Renders the AI Translator Admin dashboard via Superset iframe.
 */
class DashboardController extends ControllerBase {

  /**
   * Builds and returns the dashboard render array.
   *
   * Displays the Superset dashboard embedded via an iframe.
   *
   * @return array
   *   A Drupal render array.
   */
  public function build(): array {
    $build = [];

    // Inline stylesheet
    $build['#attached']['html_head'][] = [
      [
        '#tag'        => 'style',
        '#value'      => $this->getInlineCss(),
        '#attributes' => ['id' => 'ai-translator-dashboard-css'],
      ],
      'ai_translator_admin_dashboard_css',
    ];

    // Page wrapper
    $build['dashboard'] = [
      '#type'       => 'container',
      '#attributes' => ['class' => ['ai-dashboard']],
    ];

    // Hero header
    $build['dashboard']['header'] = [
      '#markup' => '<div class="ai-dashboard__header">
        <div class="ai-dashboard__icon">📊</div>
        <div style="flex-grow: 1;">
          <h2 class="ai-dashboard__title">Advanced Analytics Dashboard</h2>
          <p class="ai-dashboard__subtitle">Powered by Apache Superset</p>
        </div>
        <div class="ai-dashboard__actions">
          <a class="ai-dashboard__action-btn ai-dashboard__action-btn--danger"
             href="/admin/config/ai-translator/clear-cache">
            🗑️ &nbsp;Clear Redis Cache
          </a>
          <a class="ai-dashboard__action-btn"
             href="/admin/config/ai-translator/settings">
            ⚙️ &nbsp;Module Settings
          </a>
        </div>
      </div>',
    ];

    // Iframe embed for Superset
    $build['dashboard']['iframe'] = [
      '#markup' => '<div class="ai-dashboard__iframe-container">
        <iframe 
          src="http://localhost:8088/superset/dashboard/drupal/?standalone=3" 
          width="100%" 
          height="800" 
          frameborder="0" 
          allowfullscreen>
        </iframe>
      </div>',
    ];

    return $build;
  }

  /**
   * Returns the scoped inline CSS for the dashboard.
   *
   * @return string
   *   Raw CSS text.
   */
  private function getInlineCss(): string {
    return <<<CSS
/* ── AI Translator Admin Dashboard ─────────────────────────────────────── */
.ai-dashboard {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  max-width: 1200px;
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

/* Iframe container */
.ai-dashboard__iframe-container {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  background: #fff;
  border: 1px solid #e2e8f0;
}
.ai-dashboard__iframe-container iframe {
  display: block;
}
CSS;
  }

}
