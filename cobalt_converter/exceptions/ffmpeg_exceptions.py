class FFmpegError(Exception):
    pass


class FFmpegDownloadError(FFmpegError):
    pass


class FFmpegExtractionError(FFmpegError):
    pass


class UnsupportedPlatformError(FFmpegError):
    pass
