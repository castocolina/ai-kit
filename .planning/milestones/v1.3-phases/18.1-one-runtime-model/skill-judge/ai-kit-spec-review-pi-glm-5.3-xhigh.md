# Judge unavailable

judge unavailable

AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=146s out=0 tree=clean action=retry-later

The first attempt (2026-10-16) returned the same status
(`AIKIT-XAI status=capacity`, exit 75) with the provider message
`429: {"code":"1310","message":"您已达到每周/每月使用上限，您的限额将在 2026-10-21 22:10:59 重置。"}`.
The procedure's one retry ran 60 seconds later and failed the same way. This
is the second failure, recorded verbatim; the judge was not skipped silently.
