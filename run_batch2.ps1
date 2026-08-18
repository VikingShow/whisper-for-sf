$env:YUNWU_API_KEY = "sk-9J23Gmv2YZPJEzzr0sWSCJntomgOxqXmR6eIR50mpg7TMKhs"
& "C:\Users\SowrJam\AppData\Local\conda\conda\envs\fast_whisper\python.exe" -u transcribe.py `
    --dir ./audio_batch2 `
    --format docx `
    --llm-polish `
    --llm-model gpt-5.5 `
    --llm-base-url https://yunwu.ai/v1 `
    --llm-api-key-env YUNWU_API_KEY `
    --llm-search-model gpt-5.5 `
    --output-dir ./output
