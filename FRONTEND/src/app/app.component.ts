import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { RouterModule } from '@angular/router';
import { OnInit } from '@angular/core';
import { ProvaBackendService } from './prova-backend.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  message = '';
  title = 'title';

  constructor(private svc: ProvaBackendService) {}

  ngOnInit() {
    this.svc.getHello().subscribe({
      next: data => this.message = data.message,
      error: err => this.message = 'Error: ' + err.message
    });
  }
}

