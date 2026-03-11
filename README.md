# AI YouTube Content Factory (Free + GitHub)

Автоматическая фабрика faceless commentary контента для YouTube, работающая полностью в GitHub Actions.

Темы канала:
- male psychology
- discipline
- self improvement
- stoicism
- mental toughness
- success mindset

Форматы:
- Shorts: 20-45s, 9:16, 1080x1920
- Normal: 1-3 min, 16:9, 1280x720

## Архитектура

Pipeline:
1. generate idea
2. generate script + SEO
3. split script into scenes
4. download stock videos (Pexels + Pixabay)
5. generate voiceover (edge-tts with gTTS fallback)
6. generate impact captions
7. assemble video (FFmpeg)
8. generate thumbnail
9. upload + publish to YouTube

## Структура

```text
ai-youtube-factory/
  src/
    idea_generator.py
    script_generator.py
    scene_generator.py
    voice_generator.py
    stock_fetcher.py
    ffmpeg_builder.py
    caption_generator.py
    thumbnail_generator.py
    youtube_uploader.py
  pipeline/
    generate_video.py
  config/
    settings.py
  assets/
    music/
  .github/workflows/
    generate_video.yml
  requirements.txt
  README.md
```

## GitHub Secrets

Добавь в Settings -> Secrets and variables -> Actions:
- GROQ_API_KEY
- PEXELS_API_KEY
- PIXABAY_API_KEY
- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

Опционально (fallback):
- OPENAI_API_KEY

Минимум для запуска:
- хотя бы один LLM ключ: `GROQ_API_KEY` или `OPENAI_API_KEY`
- хотя бы один stock ключ: `PEXELS_API_KEY` или `PIXABAY_API_KEY`

## Настройка YouTube API

1. В Google Cloud включи YouTube Data API v3.
2. Создай OAuth Client ID (Web application).
3. Получи refresh token для аккаунта канала.
4. Заполни secrets в репозитории.

## Запуск

Автоматически:
- cron: каждые 3 часа.
- по умолчанию: 1 видео за запуск, тип `auto` (случайно short или normal), privacy `public`.

Вручную:
- Actions -> Generate and Publish Video -> Run workflow.
- Можно задать:
  - video_type: auto, short или normal
  - count: число видео
  - privacy_status: public, private или unlisted

## Массовая генерация

`pipeline/generate_video.py` поддерживает:
- `generate_multiple_videos(n)`
- CLI: `python -m pipeline.generate_video --video-type auto --privacy-status private --count 3`

## Оптимизация CI

- Groq как основной LLM (быстрее и дешевле в CI)
- FFmpeg вместо тяжелого MoviePy рендера
- H.264 + veryfast + CRF 21 (лучше качество)
- Очистка временных файлов после генерации
- Concurrency control: не допускает наложения запусков

## Качество аудио и субтитров

- Мужской voice: приоритет более естественных Edge голосов (Andrew/Brian/Guy).
- Если edge-tts временно недоступен, включается fallback на gTTS.
- Для long видео субтитры автоматически короче и с `fix_bounds`, чтобы не выходили за кадр.
- Если в `assets/music` нет треков, добавляется мягкий fallback audio bed, чтобы ролик не был без фона.
- Голос проходит loudness-нормализацию, музыка автоматически ducked под voice (sidechain compress).
- Subtitles переведены в karaoke-формат (подсветка слов по времени), с безопасными отступами для Shorts и long.
- Голос дополнительно ускоряется и делается ниже по тону (мужской стиль подачи).

## Релевантность стоков

- Включен blacklist нерелевантных категорий (makeup/beauty/skincare/cosmetics и т.д.).
- Поиск и ранжирование клипов выполняется с male-priority (man/male/men/masculine).
- Дополнительно блокируются female-oriented ключи (woman/women/female/girl/lady), чтобы визуал соответствовал мужской тематике.

Для лучшего результата добавьте 1-2 royalty-free трека в `assets/music` (`.mp3/.wav/.m4a`).

## Потенциальная монетизация

Рекомендации:
1. Делай короткий агрессивный hook в первые 1-2 секунды.
2. Меняй сцену каждые 2-3 секунды.
3. Используй 1-строчные impact captions.
4. Держи clear CTA в конце (subscribe/save/comment).

## Дополнительные retention-улучшения

- A/B идея: генерируются несколько вариантов и выбирается лучший hook по скорингу.
- Антидубли: pipeline пытается получить последние заголовки канала и штрафует похожие варианты.
