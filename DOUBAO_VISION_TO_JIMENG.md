# Doubao Vision + Jimeng Image Workflow

This workflow is intentionally split:

- `Doubao` does **image understanding / reverse prompt**.
- `Jimeng` does **image generation**.

## 1. What To Configure

### `config/system_config.json`

Set `doubao_vision`:

```json
"doubao_vision": {
  "api_key": "",
  "api_key_env": "ARK_API_KEY",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "model": "doubao-seed-1-6-vision-250815",
  "timeout_sec": 120,
  "max_retries": 1
}
```

- Recommended: keep `api_key` empty and set env var `ARK_API_KEY`.
- Default model is quality-first for visual analysis.

### `config/workflow_config*.json`

Set prompt mode:

```json
"image_prompt_mode": "doubao_reverse",
"reference_images": [
  "E:/your_refs/look_01.jpg",
  "E:/your_refs/look_02.jpg"
],
"prompt_reverse": {
  "style_preset": "menswear_showcase",
  "target_aspect_ratio": "9:16",
  "target_model": "jimeng-4.5",
  "language": "zh",
  "max_reference_images": 3,
  "extra_instruction": "Keep premium ecommerce style and clean studio light."
}
```

If you want old behavior, set:

```json
"image_prompt_mode": "manual"
```

and keep `image_prompt` / `image_negative_prompt`.

## 2. Runtime Behavior

When `image_prompt_mode=doubao_reverse`:

1. Pipeline reads `reference_images`.
2. Calls Doubao vision model to reverse engineer style.
3. Writes output to `outputs/<book>/prompt_reverse_result.json`.
4. Uses returned `jimeng_prompt` + `jimeng_negative_prompt`.
5. Calls existing Jimeng generator to produce image.

Fallback rule:

- If reverse result has empty prompt but manual `image_prompt` exists, pipeline uses manual prompt.
- If reverse fails, pipeline exits with explicit error.

## 3. Outputs Added

- `prompt_reverse_result.json`: full reverse-prompt payload and parsed fields.
- `job_output.json` now includes:
  - `image_prompt_final`
  - `image_negative_prompt_final`
  - `prompt_reverse_report` (when reverse mode is enabled)

## 4. Recommended Settings For Your Delivery Stages

- `试剪`:
  - model: `doubao-seed-1-6-flash-250828`
  - `max_reference_images`: `2`
  - faster iteration, lower cost.

- `开剪`:
  - model: `doubao-seed-1-6-vision-250815`
  - `max_reference_images`: `3`
  - better consistency and styling details.

