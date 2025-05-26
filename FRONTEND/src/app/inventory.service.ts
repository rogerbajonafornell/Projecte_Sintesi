import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

// Interfaces per a estructurar les dades que arriben del backend

// Representa un article d'inventari
export interface Article {
  CodigoArticulo: number;
  DescripcionArticulo: string;
  PVP: number;              // Preu de venda al públic
  Unidades: number;         // Quantitat en estoc
}

// Representa un usuari
export interface Usuari {
  UserId: number;
  FirstName: string;
  Username: string;
}

// Representa una comanda feta per un usuari sobre un article
export interface Comanda {
  ComandaId: number;
  User: Usuari;
  Article: Article;
  Quantitat: number;
  PreuFinal: number;
}

// Servei injectable disponible a tota l'aplicació
@Injectable({ providedIn: 'root' })
export class InventoryService {
  // URL base de l'API, definida a environments/environment.ts
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Obté tots els articles
  getArticles() {
    return this.http.get<Article[]>(`${this.apiUrl}/inventari/articles/`);
  }

  // Afegeix un nou article (sense enviar l'ID, ja que el genera el servidor)
  addArticle(article: Omit<Article, 'CodigoArticulo'>) {
    return this.http.post<Article>(`${this.apiUrl}/inventari/articles/`, article);
  }

  // Elimina un article pel seu codi
  deleteArticle(id: number) {
    return this.http.delete(`${this.apiUrl}/inventari/articles/${id}/`);
  }

  // Actualitza un article existent
  updateArticle(article: Article) {
    return this.http.put<Article>(
      `${this.apiUrl}/inventari/articles/${article.CodigoArticulo}/`,
      article
    );
  }

  // Obté la llista d'usuaris
  getUsuaris() {
    return this.http.get<Usuari[]>(`${this.apiUrl}/bot/usuaris/`);
  }

  // Obté la llista de comandes
  getComandes() {
    return this.http.get<Comanda[]>(`${this.apiUrl}/bot/comandes/`);
  }

  // Elimina una comanda pel seu identificador
  deleteOrder(id: number) {
    return this.http.delete(`${this.apiUrl}/bot/comandes/${id}/`);
  }
}
