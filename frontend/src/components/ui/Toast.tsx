import { useEffect, useState } from 'react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  type: ToastType;
  onClose: () => void;
}

export function Toast({ message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg = type === 'success' ? 'bg-dusty-olive' : type === 'error' ? 'bg-oxblood' : 'bg-air-force-blue';

  return (
    <div className={`fixed top-4 right-4 z-50 ${bg} text-white px-5 py-3 rounded-lg shadow-lg font-body text-sm flex items-center gap-3`}>
      <span>{message}</span>
      <button onClick={onClose} className="opacity-70 hover:opacity-100 text-lg leading-none">&times;</button>
    </div>
  );
}

// Hook for managing toasts
export function useToast() {
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
  const show = (message: string, type: ToastType = 'info') => setToast({ message, type });
  const clear = () => setToast(null);
  return { toast, show, clear };
}
