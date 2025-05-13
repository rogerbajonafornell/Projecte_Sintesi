import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { RouterModule } from '@angular/router';
import { OnInit } from '@angular/core';
import { ProvaBackendService } from './prova-backend.service';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterModule, TranslateModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  message = '';
  title = 'title';
  currentLang!: string;
  currentYear = new Date().getFullYear();

  constructor(private svc: ProvaBackendService, private translate: TranslateService) {
    this.currentLang = 'es'
    this.translate.setDefaultLang(this.currentLang);
    this.translate.use(this.currentLang);
  }

  switchLang(lang: any) {
    this.currentLang = lang;
    this.translate.use(lang);
  }

  ngOnInit() {
    this.svc.getHello().subscribe({
      next: data => this.message = data.message,
      error: err => this.message = 'Error: ' + err.message
    });
  }
}

