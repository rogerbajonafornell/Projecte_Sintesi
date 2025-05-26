import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  // Injecció del servei de traducció
  private translate = inject(TranslateService);

  // Signal reactiva que emmagatzema el títol traduït
  translatedTitle = signal<string>('');

  // Subscripció per escoltar els canvis d'idioma
  private langSub: Subscription;

  // Constructor: carrega la traducció inicial i escolta els canvis d'idioma
  constructor() {
    this.loadTranslations(); // Traducció inicial

    // Recarrega la traducció quan es canvia l'idioma
    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });
  }

  // Carrega la traducció de la clau 'ORDERS.TITLE' i actualitza el signal
  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  // Es crida automàticament quan el component es destrueix; allibera la subscripció
  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
