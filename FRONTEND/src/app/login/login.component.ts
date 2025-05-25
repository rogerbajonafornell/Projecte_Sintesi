import { Component, inject, signal } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../login.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
})
export class LoginComponent {
  // Formulari reactiu
  loginForm: FormGroup;

  // Missatge d'error i indicador de càrrega
  error: string | null = null;
  loading = false;

  // Traducció reactiva del títol
  private translate = inject(TranslateService);
  translatedTitle = signal<string>('');

  // Subscripció per escoltar canvis d'idioma
  private langSub: Subscription;

  // Constructor: inicialitza formulari, carrega traduccions i subscriu a canvis d'idioma
  constructor(
    private auth: AuthService,
    private router: Router,
    private fb: FormBuilder
  ) {
    this.loadTranslations();

    this.langSub = this.translate.onLangChange.subscribe(() => {
      this.loadTranslations();
    });

    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
    });
  }

  // Carrega la traducció per a la clau 'ORDERS.TITLE'
  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  // Gestiona l'enviament del formulari de login
  onSubmit() {
    if (this.loginForm.invalid) return;

    const { username, password } = this.loginForm.value;
    this.loading = true;
    this.error = null;

    // Fa la petició de login i gestiona l'èxit o error
    this.auth.login(username, password).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/home']); // Redirigeix a la pàgina d'inici
      },
      error: () => {
        this.loading = false;
        this.error = 'Credenciales inválidas'; // Mostra error si falla l'autenticació
      },
    });
  }

  // Neteja la subscripció al destruir el component
  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
