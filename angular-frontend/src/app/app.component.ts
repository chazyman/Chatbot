import { Component } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from './chat.service';

// Material-Module
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatIconModule } from '@angular/material/icon';

interface Message {
  role: string;
  content: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  // Hier binden wir alle benötigten Imports ein:
  imports: [
    NgIf,
    NgFor,
    FormsModule,
    BrowserAnimationsModule,
    MatButtonModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  chatOpen = false;
  userInput = '';
  messages: Message[] = [];
  sessionId: string | null = null;
  loading = false;
  selectedImage: File | null = null;
  imageBase64: string | undefined = undefined;

  constructor(private chatService: ChatService) {}

  async onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      this.selectedImage = file;
      this.imageBase64 = await this.convertFileToBase64(file);
    }
  }

  private convertFileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64String = result.split(',')[1];
        resolve(base64String);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  toggleChat() {
    this.chatOpen = !this.chatOpen;
    if (this.chatOpen) {
      this.sessionId = null;
      this.messages = [];
      this.chatService.getCheckpointId().subscribe({
        next: (res) => {
          this.sessionId = res.thread_id;
        },
        error: (err) => {
          console.error('Fehler beim Laden der Checkpoint-ID:', err);
        },
      });
    }
  }

  async sendMessage() {
    const input = this.userInput.trim();
    if (!input || !this.sessionId) return;

    this.loading = true;
    this.messages.push({ role: 'user', content: input });

    try {
      const response = await this.chatService
        .sendMessage(this.sessionId, input, this.imageBase64)
        .toPromise();

      if (response) {
        this.messages.push({ role: 'assistant', content: response.answer });
      }
    } catch (error) {
      console.error('Error sending message:', error);
      this.messages.push({
        role: 'error',
        content: 'Sorry, there was an error processing your request.'
      });
    } finally {
      this.loading = false;
      this.userInput = '';
      this.selectedImage = null;
      this.imageBase64 = undefined;
    }
  }
}
