import "./globals.css";
import { AuthProvider } from "./context/AuthContext";

export const metadata = {
  title: "KVPL — Tea Plantation Management",
  description: "Input & Resource Optimization System for Sri Lankan Tea Plantations"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
