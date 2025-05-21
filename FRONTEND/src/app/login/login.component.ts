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
  loginForm: FormGroup;
  error: string | null = null;
  loading = false;
  private translate = inject(TranslateService);
  translatedTitle = signal<string>('');
  private langSub: Subscription;

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

  loadTranslations() {
    this.translate.get('ORDERS.TITLE').subscribe((res: string) => {
      this.translatedTitle.set(res);
    });
  }

  onSubmit() {
    if (this.loginForm.invalid) return;

    const { username, password } = this.loginForm.value;
    this.loading = true;
    this.error = null;

    this.auth.login(username, password).subscribe({
      next: () => {
        console.log("molt be")
        this.loading = false;
        this.router.navigate(['/home']);
      },
      error: () => {
        this.loading = false;
        this.error = 'Credenciales inválidas';
      },
    });
  }

  ngOnDestroy() {
    this.langSub?.unsubscribe();
  }
}
