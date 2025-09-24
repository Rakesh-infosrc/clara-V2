import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface WelcomeProps {
  disabled: boolean;
  startButtonText: string;
  onStartCall: () => void;
}

export const Welcome = ({
  disabled,
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeProps) => {
  return (
    <section
      ref={ref}
      inert={disabled}
      className={cn(
        'bg-background fixed inset-0 mx-auto flex h-svh flex-col items-center justify-center text-center',
        disabled ? 'z-10' : 'z-20'
      )}
    >
      <svg
        width="64"
        height="64"
        viewBox="0 0 64 64"
        xmlns="http://www.w3.org/2000/svg"
        className="mb-4 size-16"
      >
        <defs>
          <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#FFFFFF" />
          </linearGradient>
        </defs>

        {[9, 20, 31, 42, 53].map((x, i) => (
          <rect
            key={i}
            x={x}
            y="20"
            width="6"
            height="24"
            rx="3"
            fill="url(#barGradient)" // Applying linear gradient fill
          >
            <animate
              attributeName="height"
              values="10;40;10"
              dur={`${1 + i * 0.4}s`}
              repeatCount="indefinite"
            />
            <animate
              attributeName="y"
              values="34;14;34"
              dur={`${1 + i * 0.4}s`}
              repeatCount="indefinite"
            />
          </rect>
        ))}
      </svg>




      <p className="text-fg1 max-w-prose pt-1 leading-6 font-medium">
        Chat live with our{' '}
        <span className="text-blue-400 font-bold text-[20px]">Clara</span>{' '}
        virtual receptionist
      </p>
      <Button variant="primary" size="lg" onClick={onStartCall} className="mt-6 w-64 font-mono bg-blue-100 text-[15px] font-bold ">
        {startButtonText}
      </Button>
      <footer className="fixed bottom-5 left-0 z-20 flex w-full items-center justify-center">
        <p className="text-fg1 max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Need help getting set up like this ? Check out the{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.infoservices.com/"
            className="underline text-blue-400"
          >
            Info Services 
          </a>
          .
        </p>
      </footer>
    </section>
  );
};
