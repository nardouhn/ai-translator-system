<?php

namespace Drupal\translator_admin\Controller;

use Drupal\Core\Controller\ControllerBase;
use Symfony\Component\DependencyInjection\ContainerInterface;
use GuzzleHttp\ClientInterface;

class DashboardController extends ControllerBase {

  protected $httpClient;
  protected $apiBaseUrl;

  public function __construct(ClientInterface $http_client) {
    $this->httpClient = $http_client;
    $this->apiBaseUrl = 'http://api:8000/api/v1';
  }

  public static function create(ContainerInterface $container) {
    return new static(
      $container->get('http_client')
    );
  }

  public function dashboard() {
    $request = \Drupal::request();

    $date_from = $request->query->get('date_from', date('Y-m-d', strtotime('-30 days')));
    $date_to   = $request->query->get('date_to',   date('Y-m-d'));
    $domain_id = $request->query->get('domain',    '');
    $page      = max(1, (int) $request->query->get('page', 1));

    \Drupal::logger('translator_admin')->notice('Dashboard called with filters: @filters', [
      '@filters' => json_encode(compact('date_from','date_to','domain_id','page'))
    ]);

    return $this->fetchDashboardFromApi($date_from, $date_to, $domain_id, $page);
  }

  private function fetchDashboardFromApi(string $date_from, string $date_to, string $domain_id, int $page): array {
    try {
      $query = [
        'date_from' => $date_from,
        'date_to'   => $date_to,
        'domain_id' => $domain_id !== '' ? (int) $domain_id : NULL,
        'page'      => $page,
      ];
      $query = array_filter($query, function($v) { return $v !== NULL; });

      $url = $this->apiBaseUrl . '/dashboard/stats';
      \Drupal::logger('translator_admin')->notice('Calling API: @url with @query', [
        '@url' => $url,
        '@query' => json_encode($query),
      ]);

      $response = $this->httpClient->get($url, [
        'query' => $query,
        'timeout' => 10,
      ]);

      $data = json_decode($response->getBody(), TRUE);

      return [
        '#theme'    => 'translator_dashboard',
        '#cache'    => [
          'contexts' => ['url.query_args'],
          'max-age'  => 0,
        ],
        '#attached' => ['library' => ['translator_admin/translation_dashboard']],
        '#stats'               => $data['stats'] ?? [],
        '#domain_distribution' => $data['domain_distribution'] ?? [],
        '#recent_logs'         => $data['recent_logs'] ?? [],
        '#failed_stats'        => $data['failed_stats'] ?? [],
        '#chart_data'          => [
          'domain_labels' => array_column($data['domain_distribution'] ?? [], 'domain_name'),
          'domain_counts' => array_column($data['domain_distribution'] ?? [], 'request_count'),
        ],
        '#filters'             => [
          'date_from'       => $date_from,
          'date_to'         => $date_to,
          'selected_domain' => $domain_id,
          // selected_model đã bỏ, để null hoặc không dùng
          'selected_model'  => null,
        ],
        '#available_domains'   => $data['available_domains'] ?? [],
        // available_models giữ nguyên (nếu API vẫn trả về) nhưng template sẽ không hiển thị nếu không có filter
        '#available_models'    => $data['available_models'] ?? [],
        '#log_total_pages'     => $data['log_pagination']['total_pages'] ?? 1,
        '#log_current_page'    => $page,
      ];
    }
    catch (\Exception $e) {
      \Drupal::logger('translator_admin')->error('Dashboard API error: @msg', ['@msg' => $e->getMessage()]);
      return [
        '#theme'    => 'translator_dashboard',
        '#cache'    => ['max-age' => 0],
        '#attached' => ['library' => ['translator_admin/translation_dashboard']],
        '#stats'               => ['total_requests' => 0, 'success_count' => 0, 'failed_count' => 0, 'pending_count' => 0, 'success_rate' => 0],
        '#domain_distribution' => [],
        '#recent_logs'         => [],
        '#failed_stats'        => [],
        '#chart_data'          => ['domain_labels' => [], 'domain_counts' => []],
        '#filters'             => [
          'date_from'       => $date_from,
          'date_to'         => $date_to,
          'selected_domain' => $domain_id,
          'selected_model'  => null,
        ],
        '#available_domains'   => [],
        '#available_models'    => [],
        '#log_total_pages'     => 0,
        '#log_current_page'    => $page,
      ];
    }
  }
}