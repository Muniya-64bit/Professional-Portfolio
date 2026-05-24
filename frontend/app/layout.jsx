import "./globals.css";

export const metadata = {
  title: "Professional Portfolio",
  description: "Portfolio built with Next.js and Flask"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
