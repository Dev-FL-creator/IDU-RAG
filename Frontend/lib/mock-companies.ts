import { Company } from "@/types/company"

export const mockCompanies: Company[] = [
  {
    id: "1",
    name: "TechVision AI",
    icon: "https://api.dicebear.com/7.x/initials/svg?seed=TechVision&backgroundColor=4F46E5",
    shortDescription: "Leading AI solutions provider specializing in computer vision and natural language processing.",
    fullDescription: "TechVision AI is at the forefront of artificial intelligence innovation, developing cutting-edge solutions that transform how businesses interact with data and customers. Our flagship products include advanced computer vision systems for manufacturing quality control and NLP engines powering next-generation chatbots.\n\nWith over 500 enterprise clients worldwide, we're committed to making AI accessible and practical for businesses of all sizes. Our team of PhDs and industry experts work tirelessly to push the boundaries of what's possible with machine learning.",
    industry: "Artificial Intelligence",
    founded: "2018",
    location: "San Francisco, CA",
    website: "https://techvisionai.example.com",
    images: [
      {
        url: "/images/figures/test.jpg",
        alt: "TechVision AI headquarters",
        caption: "Our state-of-the-art research facility in Silicon Valley",
      },
      {
        url: "/images/figures/test.jpg",
        alt: "AI research lab",
        caption: "Team working on next-gen computer vision models",
      },
    ],
    metrics: [
      { label: "Revenue", value: "$50M", trend: "up" },
      { label: "Employees", value: "250+", trend: "up" },
      { label: "Clients", value: "500+", trend: "up" },
      { label: "Growth Rate", value: "150%", trend: "up" },
    ],
  },
  {
    id: "2",
    name: "GreenEnergy Solutions",
    icon: "https://api.dicebear.com/7.x/initials/svg?seed=GreenEnergy&backgroundColor=10B981",
    shortDescription: "Renewable energy company focused on solar and wind power installations for commercial clients.",
    fullDescription: "GreenEnergy Solutions is dedicated to accelerating the world's transition to sustainable energy. We design, install, and maintain large-scale solar and wind power systems for commercial and industrial clients.\n\nOur integrated approach combines cutting-edge renewable technology with smart grid solutions and energy storage systems. We've successfully reduced carbon emissions by over 2 million tons through our installations across North America and Europe.\n\nOur mission is to make clean energy the most economical choice for businesses while contributing to a sustainable future for generations to come.",
    industry: "Renewable Energy",
    founded: "2015",
    location: "Austin, TX",
    website: "https://greenenergysolutions.example.com",
    images: [
      {
        url: "/images/figures/test.jpg",
        alt: "Solar farm installation",
        caption: "50MW solar farm project in Nevada",
      },
      {
        url: "/images/figures/test.jpg",
        alt: "Wind turbines",
        caption: "Offshore wind installation in the Gulf of Mexico",
      },
      {
        url: "/images/figures/test.jpg",
        alt: "Control center",
        caption: "24/7 monitoring and optimization center",
      },
    ],
    metrics: [
      { label: "Capacity", value: "2.5 GW", trend: "up" },
      { label: "Projects", value: "200+", trend: "up" },
      { label: "CO2 Reduced", value: "2M tons", trend: "up" },
      { label: "Efficiency", value: "95%", trend: "neutral" },
    ],
  },
  {
    id: "3",
    name: "HealthTech Innovations",
    icon: "https://api.dicebear.com/7.x/initials/svg?seed=HealthTech&backgroundColor=EF4444",
    shortDescription: "Digital health platform providing telemedicine and remote patient monitoring solutions.",
    fullDescription: "HealthTech Innovations is revolutionizing healthcare delivery through innovative digital solutions. Our comprehensive platform connects patients with healthcare providers through secure telemedicine consultations, while our IoT-enabled devices enable continuous remote patient monitoring.\n\nWe serve over 1,000 healthcare facilities and have facilitated more than 5 million virtual consultations. Our AI-powered diagnostic assistance tools help doctors make more informed decisions, improving patient outcomes while reducing costs.\n\nOur vision is a world where quality healthcare is accessible to everyone, regardless of their location or circumstances.",
    industry: "Healthcare Technology",
    founded: "2019",
    location: "Boston, MA",
    website: "https://healthtechinnovations.example.com",
    images: [
      {
        url: "/images/figures/test.jpg",
        alt: "Telemedicine platform interface",
        caption: "User-friendly interface for virtual consultations",
      },
      {
        url: "/images/figures/test.jpg",
        alt: "Remote monitoring devices",
        caption: "Suite of IoT devices for patient monitoring",
      },
    ],
    metrics: [
      { label: "Consultations", value: "5M+", trend: "up" },
      { label: "Facilities", value: "1,000+", trend: "up" },
      { label: "Satisfaction", value: "4.8/5", trend: "up" },
      { label: "Response Time", value: "<2 min", trend: "neutral" },
    ],
  },
]
