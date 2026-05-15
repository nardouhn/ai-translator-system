<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Services;

use Drupal\Core\Config\ConfigFactoryInterface;
use GuzzleHttp\ClientInterface;
use GuzzleHttp\Exception\RequestException;

/**
 * HTTP client service for communicating with the FastAPI backend.
 *
 * Reads the base URL and API key from the module's editable configuration
 * (ai_translator_admin.settings) and proxies Guzzle requests, handling
 * errors with Drupal's logger.
 */
class FastApiClient {

  /**
   * The Guzzle HTTP client.
   *
   * @var \GuzzleHttp\ClientInterface
   */
  protected ClientInterface $httpClient;

  /**
   * The config factory service.
   *
   * @var \Drupal\Core\Config\ConfigFactoryInterface
   */
  protected ConfigFactoryInterface $configFactory;

  /**
   * Constructs a FastApiClient object.
   *
   * @param \GuzzleHttp\ClientInterface $http_client
   *   The Guzzle HTTP client (injected as @http_client).
   * @param \Drupal\Core\Config\ConfigFactoryInterface $config_factory
   *   The config factory (injected as @config.factory).
   */
  public function __construct(
    ClientInterface $http_client,
    ConfigFactoryInterface $config_factory
  ) {
    $this->httpClient = $http_client;
    $this->configFactory = $config_factory;
  }

  /**
   * Executes an authenticated HTTP request against the FastAPI backend.
   *
   * @param string $method
   *   The HTTP method (e.g. 'GET', 'POST', 'PUT', 'DELETE').
   * @param string $endpoint
   *   The API endpoint path, e.g. '/api/v1/translate'. The configured
   *   base URL will be prepended automatically.
   * @param array $options
   *   Additional Guzzle request options (e.g. 'json', 'query', 'headers').
   *   Options are merged with the default headers; caller-supplied headers
   *   will NOT override the Authorization header.
   *
   * @return \Psr\Http\Message\ResponseInterface|null
   *   The Guzzle response object on success, or NULL on failure.
   */
  public function request(string $method, string $endpoint, array $options = []): ?\Psr\Http\Message\ResponseInterface {
    // Load settings from module config.
    $config = $this->configFactory->get('ai_translator_admin.settings');
    $base_url = rtrim((string) $config->get('fastapi_base_url'), '/');
    $api_key  = (string) $config->get('fastapi_api_key');

    // Build the fully-qualified URL.
    $url = $base_url . '/' . ltrim($endpoint, '/');

    // Inject the API key as a Bearer token. Merge with any caller-supplied
    // headers, but always enforce our Authorization header.
    $default_headers = [
      'Authorization' => 'Bearer ' . $api_key,
      'Accept'        => 'application/json',
    ];

    // Merge headers: caller headers are merged in but Authorization stays ours.
    if (isset($options['headers']) && is_array($options['headers'])) {
      $options['headers'] = array_merge($options['headers'], $default_headers);
    }
    else {
      $options['headers'] = $default_headers;
    }

    try {
      return $this->httpClient->request($method, $url, $options);
    }
    catch (RequestException $e) {
      \Drupal::logger('ai_translator_admin')->error(
        'FastAPI request failed [@method @url]: @message',
        [
          '@method'  => strtoupper($method),
          '@url'     => $url,
          '@message' => $e->getMessage(),
        ]
      );
      return NULL;
    }
  }

}
