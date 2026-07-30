import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = (requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000").split(",")[0].trim();
  const protocol = (requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") || host.startsWith("127.0.0.1") ? "http" : "https")).split(",")[0].trim();
  const base = new URL(`${protocol}://${host}`);
  const title = "RxMarketIQ | Medicare Part D Market Analytics";
  const description = "Real-world Medicare Part D prescriber and diabetes pharmaceutical market analytics, 2022–2024.";
  const socialImage = new URL("/og.png", base).toString();
  return {
    metadataBase: base,
    title,
    description,
    icons: { icon: "/favicon.svg" },
    openGraph: { title, description, type: "website", url: base, images: [{ url: socialImage, width: 1536, height: 1024, alt: "RxMarketIQ Medicare Part D Market Analytics" }] },
    twitter: { card: "summary_large_image", title, description, images: [socialImage] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
