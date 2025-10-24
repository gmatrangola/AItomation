export interface ErrorContext {
    [key: string]: string | number | boolean | undefined;
    provider?: string;
    model?: string;
    hostname?: string;
    port?: number;
    url?: string;
    timeout?: number;
    status_code?: number;
    details?: string;
}

export interface APIError {
    error_code: string;
    context: ErrorContext;
}
