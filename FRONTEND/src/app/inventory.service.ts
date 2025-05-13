import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

export interface Article {
  CodigoArticulo: number;
  DescripcionArticulo: string;
  PVP: number;
  Unidades: number;
}

export interface Usuari {
  UserId: number;
  FirstName: string;
  Username: string;
}

export interface Comanda {
  ComandaId: number;
  User: Usuari;
  Article: Article;
  Quantitat: number;
  PreuFinal: number;
  
}

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getArticles() {
    return this.http.get<Article[]>(`${this.apiUrl}/api/inventari/articles/`);
  }

  addArticle(article: Omit<Article, 'CodigoArticulo'>) {
    return this.http.post<Article>(`${this.apiUrl}/api/inventari/articles/`, article);
  }  

  deleteArticle(id: number) {
    return this.http.delete(`${this.apiUrl}/api/inventari/articles/${id}/`);
  }

  updateArticle(article: Article) {
    return this.http.put<Article>(
      `${this.apiUrl}/api/inventari/articles/${article.CodigoArticulo}/`,
      article
    );
  }
  
  getUsuaris() {
    return this.http.get<Usuari[]>(`${this.apiUrl}/api/bot/usuaris/`);
  }

  getComandes() {
    return this.http.get<Comanda[]>(`${this.apiUrl}/api/bot/comandes/`);
  }

  deleteOrder(id: number) {
    return this.http.delete(`${this.apiUrl}/api/bot/comandes/${id}/`);
  }
}
