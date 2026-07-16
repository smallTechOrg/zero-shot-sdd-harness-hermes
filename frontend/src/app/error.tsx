"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main className="mx-auto max-w-2xl p-8">
          <h1 className="text-2xl font-semibold">Something went wrong.</h1>
          <p className="mt-2 text-sm">
            Try again — and if it keeps failing, switch to a shorter question.
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm text-white"
          >
            Retry
          </button>
        </main>
      </body>
    </html>
  );
}
