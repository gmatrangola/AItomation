export interface DashboardSummary {
    id?: string;
    url_path: string | null;
    title?: string;
    mode?: string;
}

export interface ApplyDashboardPayload {
    config_yaml: string;
    url_path?: string | null;
    title?: string;
    create?: boolean;
}

export interface ApplyDashboardResult {
    success: boolean;
    url_path?: string | null;
    error?: string;
    error_code?: string;
}

export class DashboardService {
    /** List existing Lovelace dashboards. */
    async listDashboards(): Promise<DashboardSummary[]> {
        try {
            const response = await fetch('api/dashboards');
            if (!response.ok) {
                console.error('[DashboardService] listDashboards non-OK', response.status);
                return [];
            }
            const data = await response.json();
            return Array.isArray(data) ? data : [];
        } catch (e) {
            console.error('[DashboardService] listDashboards error', e);
            return [];
        }
    }

    /** Create and/or save a dashboard config. */
    async applyDashboard(payload: ApplyDashboardPayload): Promise<ApplyDashboardResult> {
        try {
            const response = await fetch('api/apply_dashboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || data.context?.details || 'Failed to apply dashboard',
                    error_code: data.error_code,
                };
            }
            return { success: true, url_path: data.url_path };
        } catch (e) {
            console.error('[DashboardService] applyDashboard error', e);
            return { success: false, error: e instanceof Error ? e.message : 'Failed to apply dashboard' };
        }
    }
}

export const dashboardService = new DashboardService();
