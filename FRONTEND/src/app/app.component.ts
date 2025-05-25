import { Component } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { RouterModule } from '@angular/router';
import { OnInit } from '@angular/core';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from './login.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterModule, TranslateModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  message = ''; // Missatge rebut del backend
  title = 'title'; // Nom genèric per a la pàgina (no s'està usant)
  currentLang!: string; // Idioma actual seleccionat per a la traducció
  currentYear = new Date().getFullYear(); // Any actual per a mostrar al peu de pàgina, si cal

  constructor(
    private translate: TranslateService,         // Servei de traducció ngx-translate
    public authService: AuthService,             // Servei d'autenticació
    private router: Router                       // Servei de navegació
  ) {
    // Idioma per defecte
    const savedLang = localStorage.getItem('lang') || 'es';
    this.currentLang = savedLang;
    this.translate.setDefaultLang(this.currentLang);
    this.translate.use(this.currentLang);
  }

  // Canvia l'idioma actual
  switchLang(lang: string) {
  this.currentLang = lang;
  this.translate.use(lang);
  localStorage.setItem('lang', lang); // Guarda el idioma a loclastorage
  }

  // Tanca la sessió i redirigeix a /login
  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
