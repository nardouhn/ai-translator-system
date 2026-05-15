<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\ai_translator_admin\Services\FastApiClient;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Renders a segment-by-segment comparison audit for a translated file.
 *
 * Fetches /api/files/{file_id}/segments from the FastAPI backend and
 * displays the results in a Drupal #type => 'table' render element with
 * source text and translated text in side-by-side columns.
 */
class FileAuditController extends ControllerBase {

  /**
   * The FastAPI client service.
   *
   * @var \Drupal\ai_translator_admin\Services\FastApiClient
   */
  protected FastApiClient $apiClient;

  /**
   * Constructs a FileAuditController object.
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
   * Returns the page title for a given file audit.
   *
   * Drupal calls this method when _title_callback is set in routing.yml so
   * that the file ID appears in the <h1> and <title> tags.
   *
   * @param string $file_id
   *   The file identifier from the route parameter.
   *
   * @return string
   *   The translated page title.
   */
  public function title(string $file_id): string {
    return (string) $this->t('File Audit — #@id', ['@id' => $file_id]);
  }

  /**
   * Builds the segment comparison render array.
   *
   * @param string $file_id
   *   The file identifier passed from the route parameter {file_id}.
   *
   * @return array
   *   A Drupal render array.
   */
  public function viewSegments(string $file_id): array {
    $build = [];

    // Attach our external CSS library (defined in ai_translator_admin.libraries.yml).
    $build['#attached']['library'][] = 'ai_translator_admin/admin_styles';

    // ── 1. Fetch segments from the FastAPI backend ───────────────────────────
    $segments  = [];
    $has_error = FALSE;

    $response = $this->apiClient->request('GET', "/api/files/{$file_id}/segments");

    if ($response === NULL) {
      $has_error = TRUE;
      $this->messenger()->addError(
        $this->t('Could not reach the FastAPI backend. No segment data available.')
      );
    }
    elseif ($response->getStatusCode() === 404) {
      $has_error = TRUE;
      $this->messenger()->addWarning(
        $this->t('File #@id was not found on the backend.', ['@id' => $file_id])
      );
    }
    elseif ($response->getStatusCode() !== 200) {
      $has_error = TRUE;
      $this->messenger()->addError(
        $this->t('Unexpected backend response: HTTP @code.', ['@code' => $response->getStatusCode()])
      );
    }
    else {
      $body     = (string) $response->getBody();
      $decoded  = json_decode($body, TRUE);
      $segments = is_array($decoded) ? $decoded : [];
    }

    // ── 2. Page header ───────────────────────────────────────────────────────
    $build['header'] = [
      '#markup' => '<div class="ait-audit__header">
        <div class="ait-audit__header-meta">
          <span class="ait-audit__badge">📄 File ID</span>
          <code class="ait-audit__file-id">' . htmlspecialchars($file_id, ENT_QUOTES, 'UTF-8') . '</code>
        </div>
        <a class="ait-audit__back-btn" href="/admin/config/ai-translator/dashboard">
          ← Dashboard
        </a>
      </div>',
    ];

    // ── 3. Early return on error / empty ─────────────────────────────────────
    if ($has_error || empty($segments)) {
      $build['empty'] = [
        '#markup' => '<div class="ait-audit__empty">
          <span class="ait-audit__empty-icon">🔍</span>
          <p>' . ($has_error
            ? $this->t('Segment data could not be loaded. Check the connection settings and try again.')
            : $this->t('No segments found for this file.'))
          . '</p>
        </div>',
      ];
      return $build;
    }

    // ── 4. Summary bar ───────────────────────────────────────────────────────
    $segment_count = count($segments);
    $build['summary'] = [
      '#markup' => '<div class="ait-audit__summary">
        <strong>' . $this->t('@count segment(s) found', ['@count' => $segment_count]) . '</strong>
        — ' . $this->t('Review each row for translation accuracy.') . '
      </div>',
    ];

    // ── 5. Comparison table ──────────────────────────────────────────────────
    $rows = [];
    foreach ($segments as $segment) {
      // Defensive casting — the API may return numbers or nulls.
      $order      = isset($segment['segment_order']) ? (int) $segment['segment_order'] : '—';
      $source     = isset($segment['source_text'])     ? (string) $segment['source_text']     : '';
      $translated = isset($segment['translated_text']) ? (string) $segment['translated_text'] : '';

      // Flag empty translations so they are visually obvious.
      $translated_cell = $translated !== ''
        ? ['data' => $translated, 'class' => ['ait-audit__cell--translated']]
        : ['data' => $this->t('(no translation)'), 'class' => ['ait-audit__cell--empty']];

      $rows[] = [
        // Order column — centred, narrow.
        ['data' => $order, 'class' => ['ait-audit__cell--order']],
        // Source text.
        ['data' => $source, 'class' => ['ait-audit__cell--source']],
        // Translated text.
        $translated_cell,
      ];
    }

    $build['table'] = [
      '#type'       => 'table',
      '#header'     => [
        [
          'data'  => $this->t('Order'),
          'class' => ['ait-audit__th--order'],
        ],
        [
          'data'  => $this->t('Source Text (Original)'),
          'class' => ['ait-audit__th--source'],
        ],
        [
          'data'  => $this->t('Translated Text'),
          'class' => ['ait-audit__th--translated'],
        ],
      ],
      '#rows'       => $rows,
      '#empty'      => $this->t('No segments available.'),
      '#attributes' => [
        'class' => ['ait-audit__table'],
        'id'    => 'file-audit-table',
      ],
      '#sticky'     => TRUE,   // Keeps the header visible while scrolling.
    ];

    // ── 6. Footer note ───────────────────────────────────────────────────────
    $build['footer'] = [
      '#markup' => '<p class="ait-audit__footer-note">' .
        $this->t('Data sourced live from the FastAPI backend. Refresh the page to reload.') .
        '</p>',
    ];

    return $build;
  }

}
