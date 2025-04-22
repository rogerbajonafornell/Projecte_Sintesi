import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ProvaBackendService {
  constructor(private http: HttpClient) {}

  getHello() {
    return this.http.get<{ message: string }>('/api_frontend/hello/');
  }
}