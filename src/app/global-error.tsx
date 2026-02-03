'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  console.error('Global Error Captured:', error);
  return (
    <html>
      <body className="flex h-screen w-full flex-col items-center justify-center bg-background text-foreground">
        <h2 className="mb-4 text-2xl font-bold">Something went wrong!</h2>
        <p className="mb-8 text-muted-foreground">An unexpected error has occurred.</p>
        <button
          className="rounded bg-primary px-4 py-2 font-bold text-primary-foreground hover:bg-primary/90"
          onClick={() => reset()}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
