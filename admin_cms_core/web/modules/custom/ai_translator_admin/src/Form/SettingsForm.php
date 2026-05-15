<?php

declare(strict_types=1);

namespace Drupal\ai_translator_admin\Form;

use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;

/**
 * Configuration form for the AI Translator Admin module.
 *
 * Provides two text fields that are persisted to the editable config object
 * ai_translator_admin.settings:
 *  - fastapi_base_url  – The root URL of the FastAPI backend.
 *  - fastapi_api_key   – The secret API key / Bearer token.
 */
class SettingsForm extends ConfigFormBase {

  /**
   * {@inheritdoc}
   */
  public function getFormId(): string {
    return 'ai_translator_admin_settings_form';
  }

  /**
   * {@inheritdoc}
   *
   * Declares the config object(s) that this form is allowed to save.
   */
  protected function getEditableConfigNames(): array {
    return ['ai_translator_admin.settings'];
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state): array {
    $config = $this->config('ai_translator_admin.settings');

    $form['connection'] = [
      '#type'  => 'fieldset',
      '#title' => $this->t('FastAPI Backend Connection'),
    ];

    $form['connection']['fastapi_base_url'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('FastAPI Base URL'),
      '#description'   => $this->t(
        'The root URL of the FastAPI backend, e.g. <code>https://api.example.com</code>. '
        . 'Do <strong>not</strong> include a trailing slash.'
      ),
      '#default_value' => $config->get('fastapi_base_url') ?? '',
      '#required'      => TRUE,
      '#maxlength'     => 255,
      '#placeholder'   => 'https://api.example.com',
    ];

    $form['connection']['fastapi_api_key'] = [
      '#type'          => 'textfield',
      '#title'         => $this->t('API Key'),
      '#description'   => $this->t(
        'The secret API key sent as a <code>Bearer</code> token in the '
        . '<code>Authorization</code> header on every request.'
      ),
      '#default_value' => $config->get('fastapi_api_key') ?? '',
      '#required'      => TRUE,
      '#maxlength'     => 512,
      '#placeholder'   => 'sk-…',
      // Mask the field so the key is not visible in the browser DOM.
      '#attributes'    => ['autocomplete' => 'off'],
    ];

    return parent::buildForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(array &$form, FormStateInterface $form_state): void {
    parent::validateForm($form, $form_state);

    $base_url = trim($form_state->getValue('fastapi_base_url'));

    // Ensure the URL uses http or https.
    if (!empty($base_url) && !preg_match('#^https?://#i', $base_url)) {
      $form_state->setErrorByName(
        'fastapi_base_url',
        $this->t('The FastAPI Base URL must start with <code>http://</code> or <code>https://</code>.')
      );
    }
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state): void {
    $this->config('ai_translator_admin.settings')
      ->set('fastapi_base_url', trim($form_state->getValue('fastapi_base_url')))
      ->set('fastapi_api_key', trim($form_state->getValue('fastapi_api_key')))
      ->save();

    parent::submitForm($form, $form_state);
  }

}
