import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/AppShell";

const queryClient = new QueryClient();

export default function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
