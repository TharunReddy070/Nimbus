
export const siteConfig = {
  name: "NimbusAI",
  description: "AI-powered cloud architecture and implementation platform",
  logo: {
    src: "/logo.svg",
    alt: "NimbusAI Logo",
  },
  url: "https://nimbusai.cloud",
};

export const homePageConfig = {
  hero: {
    title: "Cloud Architecture & Implementation, Simplified",
    description: "Professional cloud architecture diagrams, implementation strategies, and monitoring solutions powered by AI.",
    ctaButton: "Start Building",
    ctaLink: "/chat",
  },
  services: [
    {
      title: "Cloud Architecture Diagrams",
      description: "Generate AWS, GCP, or Azure-specific diagrams based on your project description.",
      icon: "LayoutGrid",
    },
    {
      title: "Real-Time Case Studies",
      description: "Access verified case studies pulled directly from official cloud provider resources.",
      icon: "BookOpen",
    },
    {
      title: "Deep Implementation Research",
      description: "Get in-depth research on cloud platform implementations, migration strategies, and cost estimation.",
      icon: "Search",
    },
    {
      title: "Monitoring & Reporting",
      description: "Self-hosted solution for cloud credential integration, log monitoring, and natural language report generation.",
      icon: "BarChart",
    },
  ],
};

export const chatConfig = {
  templates: [
    {
      title: "AWS Architecture",
      prompt: "Design a serverless AWS architecture for an e-commerce platform with high availability requirements.",
      icon: "Cloud",
    },
    {
      title: "GCP Migration",
      prompt: "Outline a step-by-step migration plan from on-premise to Google Cloud Platform for a financial services company.",
      icon: "ArrowRightLeft",
    },
    {
      title: "Azure Cost Optimization",
      prompt: "Analyze and recommend cost optimization strategies for our Azure-based data analytics platform.",
      icon: "DollarSign",
    },
    {
      title: "Multi-Cloud Strategy",
      prompt: "Create a multi-cloud strategy that leverages AWS, GCP, and Azure for different aspects of our SaaS application.",
      icon: "Network",
    },
  ],
  scenes: {
    SCENE_1: {
      title: "AWS Architecture Diagram",
      type: "markdown",
      content: "# AWS Architecture for E-Commerce Platform\n\nBased on your requirements, I've designed a highly available, serverless architecture for your e-commerce platform.\n\n## Key Components\n\n* **Amazon CloudFront** for content delivery\n* **AWS Lambda** for serverless compute\n* **Amazon DynamoDB** for NoSQL database\n* **Amazon S3** for static content storage\n* **Amazon Cognito** for user authentication\n\n```javascript\n// Example Lambda function for product search\nexports.handler = async (event) => {\n  const searchTerm = event.queryStringParameters.query;\n  // Query DynamoDB for products\n  const results = await searchProducts(searchTerm);\n  return {\n    statusCode: 200,\n    body: JSON.stringify(results)\n  };\n};\n```\n\nThis architecture ensures scalability and fault tolerance while minimizing operational overhead.",
    },
    SCENE_2: {
      title: "Cloud Migration Case Study",
      type: "image",
      imageUrl: "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?auto=format&fit=crop&w=800&q=80",
      content: "# GCP Migration Strategy: Financial Services\n\nHere's a comprehensive migration plan based on industry best practices and case studies from similar financial institutions.\n\n## Phase 1: Assessment & Planning\n* Inventory existing applications and infrastructure\n* Identify regulatory compliance requirements\n* Develop migration priorities and timeline\n\n## Phase 2: Foundation Building\n* Establish VPC and networking architecture\n* Implement IAM and security controls\n* Set up monitoring and logging\n\n## Phase 3: Migration Execution\n* Migrate non-critical applications first\n* Move databases with minimal downtime\n* Transition customer-facing applications last\n\n## Success Metrics\n* 40% reduction in operational costs\n* 99.99% uptime during migration\n* Zero security incidents during transition",
      code: "// GCP Terraform Configuration\nresource \"google_compute_network\" \"vpc_network\" {\n  name = \"financial-services-vpc\"\n  auto_create_subnetworks = false\n}\n\nresource \"google_compute_subnetwork\" \"subnet\" {\n  name = \"financial-subnet\"\n  ip_cidr_range = \"10.0.0.0/24\"\n  region = \"us-central1\"\n  network = google_compute_network.vpc_network.id\n}",
      citations: [
        {
          title: "Google Cloud for Financial Services",
          author: "Google Cloud Platform",
          year: "2023",
          url: "https://cloud.google.com/solutions/financial-services"
        },
        {
          title: "Cloud Migration Best Practices",
          author: "Gartner Research",
          year: "2022",
          url: "https://www.gartner.com/en/documents/cloud-migration-best-practices"
        }
      ]
    },
    SCENE_3: {
      title: "Cloud Cost Analysis",
      type: "canvas",
      imageUrl: "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?auto=format&fit=crop&w=800&q=80",
      content: "# Azure Cost Optimization Strategy\n\nAfter analyzing your current Azure environment, I've identified several opportunities for cost optimization without sacrificing performance.\n\n## Current Cost Breakdown\n* **Compute Resources**: 45%\n* **Storage**: 30%\n* **Networking**: 15%\n* **Other Services**: 10%\n\n## Key Recommendations\n\n1. Right-size virtual machines based on actual utilization\n2. Implement auto-scaling for workload-based resource allocation\n3. Move cold data to lower-cost storage tiers\n4. Reserve instances for predictable workloads\n\n## Estimated Annual Savings\n$120,000 (approximately 35% of current cloud spend)",
      code: "// Azure Resource Manager Template\n{\n  \"$schema\": \"https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#\",\n  \"contentVersion\": \"1.0.0.0\",\n  \"parameters\": {\n    \"vmSize\": {\n      \"type\": \"string\",\n      \"defaultValue\": \"Standard_D2s_v3\",\n      \"allowedValues\": [\n        \"Standard_B2s\",\n        \"Standard_D2s_v3\",\n        \"Standard_D4s_v3\"\n      ],\n      \"metadata\": {\n        \"description\": \"Size of the virtual machine\"\n      }\n    }\n  },\n  \"resources\": [\n    // VM definitions would go here\n  ]\n}",
      canvasContent: `<div class="article-content py-4">
        <h1 class="text-2xl font-bold mb-4">Azure Cost Optimization Analysis</h1>
        <p class="mb-4">Based on your current Azure environment, we've identified several opportunities to optimize costs while maintaining performance and reliability.</p>
        
        <h2 class="text-xl font-semibold mb-3 mt-6">Current Cost Distribution</h2>
        <div class="bg-gray-100 p-4 rounded-md mb-6">
          <canvas id="costBreakdownChart" width="600" height="300"></canvas>
          <script>
            const canvas = document.getElementById('costBreakdownChart');
            const ctx = canvas.getContext('2d');
            
            // Background
            ctx.fillStyle = '#f8fafc';
            ctx.fillRect(0, 0, 600, 300);
            
            // Draw pie chart
            const centerX = 300;
            const centerY = 150;
            const radius = 100;
            
            const data = [
              { label: 'Compute', value: 45, color: '#3b82f6' },
              { label: 'Storage', value: 30, color: '#10b981' },
              { label: 'Networking', value: 15, color: '#6366f1' },
              { label: 'Other', value: 10, color: '#f59e0b' }
            ];
            
            let startAngle = 0;
            data.forEach(segment => {
              const segmentAngle = (segment.value / 100) * 2 * Math.PI;
              
              ctx.beginPath();
              ctx.moveTo(centerX, centerY);
              ctx.arc(centerX, centerY, radius, startAngle, startAngle + segmentAngle);
              ctx.closePath();
              
              ctx.fillStyle = segment.color;
              ctx.fill();
              
              // Calculate label position
              const labelAngle = startAngle + segmentAngle/2;
              const labelRadius = radius * 0.7;
              const labelX = centerX + (labelRadius * Math.cos(labelAngle));
              const labelY = centerY + (labelRadius * Math.sin(labelAngle));
              
              // Draw percentage labels
              ctx.fillStyle = '#ffffff';
              ctx.font = 'bold 14px Arial';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(segment.value + '%', labelX, labelY);
              
              startAngle += segmentAngle;
            });
            
            // Draw legend
            const legendY = 270;
            data.forEach((segment, index) => {
              const legendX = 150 + (index * 120);
              
              // Color box
              ctx.fillStyle = segment.color;
              ctx.fillRect(legendX, legendY, 15, 15);
              
              // Label
              ctx.fillStyle = '#334155';
              ctx.font = '12px Arial';
              ctx.textAlign = 'left';
              ctx.textBaseline = 'middle';
              ctx.fillText(segment.label, legendX + 20, legendY + 7);
            });
            
            // Title
            ctx.fillStyle = '#334155';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Azure Cost Distribution', 300, 30);
          </script>
        </div>
        
        <h2 class="text-xl font-semibold mb-3">Optimization Recommendations</h2>
        <ul class="list-disc pl-5 mb-4 space-y-2">
          <li>Right-size underutilized virtual machines (potential 25% savings)</li>
          <li>Implement auto-scaling for non-production environments (potential 15% savings)</li>
          <li>Transfer cold data to Azure Archive Storage (potential 80% storage cost reduction)</li>
          <li>Purchase reserved instances for stable workloads (up to 72% discount compared to pay-as-you-go)</li>
          <li>Implement automated VM start/stop schedules for development resources (potential 70% reduction)</li>
        </ul>
        
        <h2 class="text-xl font-semibold mb-3 mt-6">Projected Cost Reduction</h2>
        <div class="bg-gray-100 p-4 rounded-md mb-6">
          <canvas id="savingsChart" width="600" height="300"></canvas>
          <script>
            const savingsCanvas = document.getElementById('savingsChart');
            const savingsCtx = savingsCanvas.getContext('2d');
            
            // Background
            savingsCtx.fillStyle = '#f8fafc';
            savingsCtx.fillRect(0, 0, 600, 300);
            
            // Data
            const currentCost = 350000;
            const projectedCost = 227500;
            const savings = currentCost - projectedCost;
            
            // Draw bars
            savingsCtx.fillStyle = '#3b82f6';
            savingsCtx.fillRect(150, 100, 100, 150);
            
            savingsCtx.fillStyle = '#10b981';
            savingsCtx.fillRect(350, 165, 100, 85);
            
            // Draw labels
            savingsCtx.fillStyle = '#334155';
            savingsCtx.font = '14px Arial';
            savingsCtx.textAlign = 'center';
            
            savingsCtx.fillText('Current Annual Cost', 200, 80);
            savingsCtx.fillText('$350,000', 200, 270);
            
            savingsCtx.fillText('Projected Annual Cost', 400, 80);
            savingsCtx.fillText('$227,500', 400, 270);
            
            // Draw savings arrow and label
            savingsCtx.beginPath();
            savingsCtx.moveTo(250, 150);
            savingsCtx.lineTo(350, 150);
            savingsCtx.strokeStyle = '#ef4444';
            savingsCtx.lineWidth = 2;
            savingsCtx.stroke();
            
            // Arrow head
            savingsCtx.beginPath();
            savingsCtx.moveTo(350, 150);
            savingsCtx.lineTo(340, 145);
            savingsCtx.lineTo(340, 155);
            savingsCtx.fillStyle = '#ef4444';
            savingsCtx.fill();
            
            savingsCtx.fillStyle = '#ef4444';
            savingsCtx.font = 'bold 14px Arial';
            savingsCtx.fillText('$122,500 Savings (35%)', 300, 135);
            
            // Title
            savingsCtx.fillStyle = '#334155';
            savingsCtx.font = 'bold 16px Arial';
            savingsCtx.textAlign = 'center';
            savingsCtx.fillText('Projected Annual Cost Savings', 300, 30);
          </script>
        </div>
        
        <h2 class="text-xl font-semibold mb-3">Implementation Timeline</h2>
        <div class="bg-gray-100 p-4 rounded-md mb-6">
          <table class="min-w-full">
            <thead>
              <tr class="border-b border-gray-300">
                <th class="text-left py-2">Phase</th>
                <th class="text-left py-2">Timeline</th>
                <th class="text-left py-2">Estimated Savings</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-gray-200">
                <td class="py-2">Quick Wins (Right-sizing, Cleanup)</td>
                <td class="py-2">1-2 weeks</td>
                <td class="py-2">$35,000</td>
              </tr>
              <tr class="border-b border-gray-200">
                <td class="py-2">Storage Optimization</td>
                <td class="py-2">2-4 weeks</td>
                <td class="py-2">$27,500</td>
              </tr>
              <tr class="border-b border-gray-200">
                <td class="py-2">Reserved Instances Purchase</td>
                <td class="py-2">Immediate</td>
                <td class="py-2">$42,000</td>
              </tr>
              <tr class="border-b border-gray-200">
                <td class="py-2">Automation Implementation</td>
                <td class="py-2">1-2 months</td>
                <td class="py-2">$18,000</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>`,
      citations: [
        {
          title: "Azure Cost Optimization Best Practices",
          author: "Microsoft",
          year: "2023",
          url: "https://docs.microsoft.com/en-us/azure/cost-management-billing/costs/cost-mgt-best-practices"
        },
        {
          title: "Cloud Cost Optimization Strategies",
          author: "Forrester Research",
          year: "2022",
          url: "https://www.forrester.com/report/cloud-cost-optimization-strategies"
        },
        {
          title: "Financial Operations Guide for Azure",
          author: "Microsoft Azure",
          year: "2023",
          url: "https://azure.microsoft.com/en-us/resources/financial-operations-guide/"
        }
      ]
    }
  },
};
