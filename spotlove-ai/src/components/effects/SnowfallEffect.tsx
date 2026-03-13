import { useEffect, useState, useCallback } from 'react';
import { useTheme } from '@/contexts/ThemeContext';

interface Snowflake {
  id: number;
  x: number;
  size: number;
  animationDuration: number;
  animationDelay: number;
  opacity: number;
  blur: number;
  wobble: number;
}

interface Sparkle {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  delay: number;
}

export function SnowfallEffect() {
  const { theme } = useTheme();
  const [snowflakes, setSnowflakes] = useState<Snowflake[]>([]);
  const [sparkles, setSparkles] = useState<Sparkle[]>([]);

  const generateSnowflakes = useCallback(() => {
    // Multiple layers of snowflakes for depth
    const flakes: Snowflake[] = [];
    
    // Background layer - smaller, slower, more blurred
    for (let i = 0; i < 30; i++) {
      flakes.push({
        id: i,
        x: Math.random() * 100,
        size: Math.random() * 3 + 1,
        animationDuration: Math.random() * 12 + 15,
        animationDelay: Math.random() * 8,
        opacity: Math.random() * 0.3 + 0.1,
        blur: 2,
        wobble: Math.random() * 30 - 15,
      });
    }
    
    // Middle layer - medium sized
    for (let i = 30; i < 70; i++) {
      flakes.push({
        id: i,
        x: Math.random() * 100,
        size: Math.random() * 4 + 2,
        animationDuration: Math.random() * 8 + 10,
        animationDelay: Math.random() * 6,
        opacity: Math.random() * 0.5 + 0.3,
        blur: 1,
        wobble: Math.random() * 40 - 20,
      });
    }
    
    // Foreground layer - larger, faster, sharper
    for (let i = 70; i < 100; i++) {
      flakes.push({
        id: i,
        x: Math.random() * 100,
        size: Math.random() * 5 + 3,
        animationDuration: Math.random() * 6 + 6,
        animationDelay: Math.random() * 4,
        opacity: Math.random() * 0.7 + 0.3,
        blur: 0,
        wobble: Math.random() * 50 - 25,
      });
    }
    
    return flakes;
  }, []);

  const generateSparkles = useCallback(() => {
    // Random sparkles across the screen
    return Array.from({ length: 20 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1,
      opacity: Math.random() * 0.8 + 0.2,
      delay: Math.random() * 5,
    }));
  }, []);

  useEffect(() => {
    if (theme === 'dark') {
      setSnowflakes(generateSnowflakes());
      setSparkles(generateSparkles());
    } else {
      setSnowflakes([]);
      setSparkles([]);
    }
  }, [theme, generateSnowflakes, generateSparkles]);

  if (theme !== 'dark' || snowflakes.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
      {/* Subtle aurora gradient at top */}
      <div 
        className="absolute top-0 left-0 right-0 h-64 opacity-20"
        style={{
          background: 'linear-gradient(180deg, rgba(100, 200, 255, 0.15) 0%, rgba(150, 100, 255, 0.1) 50%, transparent 100%)',
        }}
      />
      
      {/* Snowflakes with varied animations */}
      {snowflakes.map((flake) => (
        <div
          key={flake.id}
          className="absolute"
          style={{
            left: `${flake.x}%`,
            top: '-20px',
            animation: `snowfall ${flake.animationDuration}s linear infinite`,
            animationDelay: `${flake.animationDelay}s`,
            filter: `blur(${flake.blur}px)`,
          }}
        >
          <div 
            className="rounded-full"
            style={{
              width: `${flake.size}px`,
              height: `${flake.size}px`,
              opacity: flake.opacity,
              background: `radial-gradient(circle at 30% 30%, white 0%, rgba(200, 220, 255, 0.8) 50%, rgba(150, 180, 255, 0.4) 100%)`,
              boxShadow: `
                0 0 ${flake.size}px rgba(255, 255, 255, 0.9),
                0 0 ${flake.size * 2}px rgba(200, 220, 255, 0.6),
                0 0 ${flake.size * 3}px rgba(150, 180, 255, 0.3)
              `,
              animation: `wobble ${Math.random() * 3 + 2}s ease-in-out infinite`,
            }}
          />
        </div>
      ))}

      {/* Twinkling sparkles */}
      {sparkles.map((sparkle) => (
        <div
          key={`sparkle-${sparkle.id}`}
          className="absolute"
          style={{
            left: `${sparkle.x}%`,
            top: `${sparkle.y}%`,
            animation: `sparkle 2s ease-in-out infinite`,
            animationDelay: `${sparkle.delay}s`,
          }}
        >
          <div 
            style={{
              width: `${sparkle.size}px`,
              height: `${sparkle.size}px`,
              opacity: sparkle.opacity,
              background: 'white',
              borderRadius: '50%',
              boxShadow: `
                0 0 ${sparkle.size * 2}px white,
                0 0 ${sparkle.size * 4}px rgba(200, 220, 255, 0.8)
              `,
            }}
          />
        </div>
      ))}

      {/* Inline styles for animations */}
      <style>{`
        @keyframes wobble {
          0%, 100% { transform: translateX(0) rotate(0deg); }
          25% { transform: translateX(-10px) rotate(-5deg); }
          75% { transform: translateX(10px) rotate(5deg); }
        }
        
        @keyframes sparkle {
          0%, 100% { 
            opacity: 0.2; 
            transform: scale(0.8); 
          }
          50% { 
            opacity: 1; 
            transform: scale(1.2); 
          }
        }
      `}</style>
    </div>
  );
}