/**
 * Image Path Examples
 *
 * This file demonstrates how to reference images in your application.
 * All paths are relative to the public folder.
 */

// Avatar images
export const avatarImages = {
  user1: "/images/avatars/user1.jpg",
  user2: "/images/avatars/user2.png",
  default: "/images/avatars/default.png",
}

// Chart images
export const chartImages = {
  salesQ1: "/images/charts/sales-q1-2024.png",
  salesQ2: "/images/charts/sales-q2-2024.png",
  comparison: "/images/charts/comparison.png",
  analytics: "/images/charts/analytics.png",
}

// Icon images
export const iconImages = {
  logo: "/images/icons/logo.svg",
  logoLight: "/images/icons/logo-light.svg",
  logoDark: "/images/icons/logo-dark.svg",
}

// Background images
export const backgroundImages = {
  hero: "/images/backgrounds/hero.jpg",
  pattern: "/images/backgrounds/pattern.svg",
}

/**
 * Example: How to use in a message
 */
export const exampleMessageWithImage = {
  id: "1",
  role: "assistant" as const,
  contents: [
    {
      type: "text" as const,
      content: "Here's the sales analysis you requested:",
    },
    {
      type: "image" as const,
      content: chartImages.salesQ1,
      alt: "Q1 2024 Sales Chart",
    },
    {
      type: "text" as const,
      content: "The chart shows a 25% increase compared to last quarter.",
    },
  ],
}

/**
 * Helper function to get image path
 */
export function getImagePath(category: string, filename: string): string {
  return `/images/${category}/${filename}`
}

// Usage examples:
// getImagePath("avatars", "user1.jpg") → "/images/avatars/user1.jpg"
// getImagePath("charts", "sales.png") → "/images/charts/sales.png"
