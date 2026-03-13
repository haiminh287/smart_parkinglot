import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { 
  MessageCircle, 
  X, 
  Phone,
  ExternalLink
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Social Icons
const ZaloIcon = () => (
  <svg viewBox="0 0 48 48" className="h-5 w-5" fill="currentColor">
    <path d="M24 4C12.954 4 4 12.954 4 24s8.954 20 20 20 20-8.954 20-20S35.046 4 24 4zm0 36c-8.822 0-16-7.178-16-16S15.178 8 24 8s16 7.178 16 16-7.178 16-16 16z"/>
    <path d="M32.5 18h-17c-.828 0-1.5.672-1.5 1.5s.672 1.5 1.5 1.5h17c.828 0 1.5-.672 1.5-1.5s-.672-1.5-1.5-1.5zM32.5 23h-17c-.828 0-1.5.672-1.5 1.5s.672 1.5 1.5 1.5h17c.828 0 1.5-.672 1.5-1.5s-.672-1.5-1.5-1.5zM25.5 28h-10c-.828 0-1.5.672-1.5 1.5s.672 1.5 1.5 1.5h10c.828 0 1.5-.672 1.5-1.5s-.672-1.5-1.5-1.5z"/>
  </svg>
);

const FacebookIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const TelegramIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
  </svg>
);

interface ContactChannel {
  id: string;
  name: string;
  icon: React.ComponentType;
  color: string;
  bgColor: string;
  link: string;
}

const contactChannels: ContactChannel[] = [
  {
    id: 'zalo',
    name: 'Zalo',
    icon: ZaloIcon,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10 hover:bg-blue-500/20',
    link: 'https://zalo.me/0901234567',
  },
  {
    id: 'facebook',
    name: 'Facebook',
    icon: FacebookIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-600/10 hover:bg-blue-600/20',
    link: 'https://m.me/parksmart',
  },
  {
    id: 'telegram',
    name: 'Telegram',
    icon: TelegramIcon,
    color: 'text-sky-500',
    bgColor: 'bg-sky-500/10 hover:bg-sky-500/20',
    link: 'https://t.me/parksmart_support',
  },
  {
    id: 'hotline',
    name: 'Hotline',
    icon: Phone,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10 hover:bg-green-500/20',
    link: 'tel:19001234',
  },
];

export function ContactWidget() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-24 left-4 z-40 sm:bottom-28 sm:left-6">
      {/* Contact Options - Opens upward with proper containment */}
      <div 
        className={cn(
          "absolute bottom-[72px] left-0 flex flex-col gap-2 transition-all duration-300 max-h-[60vh] overflow-y-auto",
          isOpen 
            ? "opacity-100 translate-y-0 pointer-events-auto" 
            : "opacity-0 translate-y-4 pointer-events-none"
        )}
      >
        {contactChannels.map((channel, index) => (
          <a
            key={channel.id}
            href={channel.link}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-3 rounded-xl border border-primary/30 bg-card/95 backdrop-blur-sm px-3 py-2.5 shadow-lg transition-all duration-200 hover:scale-105 hover:border-primary hover:shadow-primary/20 animate-fade-in",
            )}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className={cn(
              "flex h-9 w-9 items-center justify-center rounded-lg text-white shadow-md shrink-0",
              channel.id === 'zalo' && "bg-blue-500",
              channel.id === 'facebook' && "bg-blue-600",
              channel.id === 'telegram' && "bg-sky-500",
              channel.id === 'hotline' && "bg-green-500",
            )}>
              <channel.icon />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground">{channel.name}</p>
              <p className="text-xs text-muted-foreground truncate">
                {channel.id === 'hotline' ? '1900 1234' : 'Nhắn tin ngay'}
              </p>
            </div>
            <ExternalLink className="h-3.5 w-3.5 text-primary shrink-0" />
          </a>
        ))}
      </div>

      {/* Main Toggle Button */}
      <Button
        size="lg"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "h-14 w-14 rounded-full shadow-xl transition-all duration-300 hover:scale-110",
          isOpen 
            ? "bg-destructive hover:bg-destructive/90" 
            : "gradient-primary"
        )}
      >
        {isOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <MessageCircle className="h-6 w-6" />
        )}
      </Button>

      {/* Pulse effect when closed */}
      {!isOpen && (
        <span className="absolute inset-0 -z-10 animate-ping rounded-full bg-primary opacity-30" />
      )}
    </div>
  );
}
