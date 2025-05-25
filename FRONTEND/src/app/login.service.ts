import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { tap } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private tokenKey = 'auth_token'; // Clau per token a localStorage
  private apiUrl = environment.apiUrl; // URL base API

  constructor(private http: HttpClient) { }

  // Login: envia usuari i password i guarda token
  login(username: string, password: string) {
    return this.http.post<any>(`${this.apiUrl}/login/`, { username, password }).pipe(
      tap(response => localStorage.setItem(this.tokenKey, response.token))
    );
  }

  // Logout: elimina token
  logout(): void {
    localStorage.removeItem(this.tokenKey);
  }

  // Comprova si hi ha token (usuari autenticat)
  isAuthenticated(): boolean {
    return !!localStorage.getItem(this.tokenKey);
  }

  // Retorna el token guardat o null
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }
}
