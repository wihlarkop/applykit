export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

class ToastState {
  toasts = $state<Toast[]>([]);

  add(message: string, type: ToastType = 'info', duration = 3000) {
    const id = crypto.randomUUID();
    const toast: Toast = { id, message, type, duration };
    this.toasts.push(toast);

    if (duration > 0) {
      setTimeout(() => {
        this.remove(id);
      }, duration);
    }
    return id;
  }

  success(message: string, duration = 3000) {
    return this.add(message, 'success', duration);
  }

  error(message: string, duration = 5000) {
    return this.add(message, 'error', duration);
  }

  info(message: string, duration = 3000) {
    return this.add(message, 'info', duration);
  }

  remove(id: string) {
    this.toasts = this.toasts.filter((t) => t.id !== id);
  }
}

export const toastState = new ToastState();
