import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ProvaBackendService {
  constructor(private http: HttpClient) {}

  getHello() {
    return this.http.get('/api_frontend/hello/', { responseType: 'text' })
      .pipe(map(text => JSON.parse(text)));
  }
}