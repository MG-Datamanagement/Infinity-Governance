import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

export type APIType = "rest" | "graphql";

class ChatApiClient {
  private restClient: AxiosInstance;
  private apiType: APIType = "rest";

  constructor() {
    this.restClient = axios.create({
      baseURL:
        process.env.NEXT_PUBLIC_CHATBOT_API_URL || "http://localhost:8000",
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor (same as dashboard)
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

    // Response interceptor
    this.restClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          window.location.href = "/login";
        }
        return Promise.reject(error);
      },
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    if (this.apiType === "rest") {
      const response = await this.restClient.get<T>(url, config);
      return response.data;
    }
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
    throw new Error("GraphQL not implemented yet");
  }
}

export const chatApiClient = new ChatApiClient();
