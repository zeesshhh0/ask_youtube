export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const errorMessages = {
  invalidUrl:
    "Hmm, that doesn't look like a valid YouTube URL. Could you try again? Example: https://www.youtube.com/watch?v=xxxxx",

  noTranscript:
    "Unfortunately, this video doesn't have captions available. I need captions to chat about the content. Try another video?",

  processingFailed:
    "I had trouble processing that video. This could be temporary. Want to try again?",

  streamingError: "Oops! My response got interrupted. Let me try that again.",

  networkError:
    "Unable to connect to the server. Please check your connection and try again.",

  unknownError: "Something went wrong. Please try again.",

  threadNotFound: "This chat thread could not be found.",

  videoTooLong: "Video is too long. Maximum allowed duration is 20 minutes.",

  rateLimited: "Too many requests. Please wait a moment and try again.",
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.statusCode) {
      case 400:
        return errorMessages.invalidUrl;
      case 404:
        return errorMessages.threadNotFound;
      case 413:
        return errorMessages.videoTooLong;
      case 422:
        return errorMessages.noTranscript;
      case 429:
        return errorMessages.rateLimited;
      case 500:
        return errorMessages.processingFailed;
      default:
        return error.message || errorMessages.unknownError;
    }
  }

  if (error instanceof TypeError && error.message.includes("fetch")) {
    return errorMessages.networkError;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return errorMessages.unknownError;
}
