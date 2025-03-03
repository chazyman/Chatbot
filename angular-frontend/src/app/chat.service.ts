import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface ChatRequest {
  thread_id: string;
  message: string;
  image?: string;  // base64 encoded image
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private baseURL = '/api';
  private apiVersion = 'v2';

  constructor(private http: HttpClient) {}

  getCheckpointId() {
    return this.http.get<{ thread_id: string }>(
      `${this.baseURL}/checkpoint_id`
    );
  }

  sendMessage(threadId: string, userMsg: string, imageBase64?: string) {
    const payload: ChatRequest = {
      thread_id: threadId,
      message: userMsg,
      image: imageBase64
    };
    
    return this.http.post<{ answer: string }>(`${this.baseURL}/${this.apiVersion}/chat`, 
      payload
    );
  }
}
