import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

export type APIType = "rest" | "graphql";

class DashboardApiClient {
  private restClient: AxiosInstance;
  private apiType: APIType = "rest";

  constructor() {
    this.restClient = axios.create({
      baseURL:
        process.env.NEXT_PUBLIC_DASHBOARD_API_URL || "http://localhost:8000",
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor for auth tokens
    this.restClient.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("auth_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Response interceptor for error handling
    this.restClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          window.location.href = "/login";
        }
        return Promise.reject(error);
      },
    );
  }

  setAPIType(type: APIType) {
    this.apiType = type;
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    if (this.apiType === "rest") {
      const response = await this.restClient.get<T>(url, config);
      return response.data;
    }
    // GraphQL implementation placeholder
    throw new Error("GraphQL not implemented yet");
  }

  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    if (this.apiType === "rest") {
      const response = await this.restClient.post<T>(url, data, config);
      return response.data;
    }
    // GraphQL implementation placeholder
    throw new Error("GraphQL not implemented yet");
  }

  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<T> {
    if (this.apiType === "rest") {
      const response = await this.restClient.put<T>(url, data, config);
      return response.data;
    }
    throw new Error("GraphQL not implemented yet");
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    if (this.apiType === "rest") {
      const response = await this.restClient.delete<T>(url, config);
      return response.data;
    }
    throw new Error("GraphQL not implemented yet");
  }

  // GraphQL specific method
  // async query<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
  //   if (this.apiType === 'graphql') {
  //     const response = await this.restClient.post<{ data: T }>('/graphql', {
  //       query,
  //       variables,
  //     });
  //     return response.data.data;
  //   }
  //   throw new Error('GraphQL mode not enabled');
  // }
}

export const dashboardApiClient = new DashboardApiClient();
