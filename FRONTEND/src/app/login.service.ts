import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { environment } from '../environments/environment';

// auth.service.ts
@Injectable({ providedIn: 'root' })
export class AuthService {
  private tokenKey = 'auth_token';

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  // auth.service.ts
  login(username: string, password: string) {
    return this.http.post<any>(`${this.apiUrl}/login/`, { username, password }).pipe(
      tap(response => {
        localStorage.setItem(this.tokenKey, response.token); // Guarda el token aquí
      })
    );
  }

  logout(): void {
    localStorage.removeItem(this.tokenKey);
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem(this.tokenKey);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }
}
