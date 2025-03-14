import React from 'react';
import { Link } from 'react-router-dom';
import { homePageConfig, siteConfig } from '@/config/content';
import { ArrowRight, LayoutGrid, BookOpen, Search, BarChart, Cloud, Server, Database, Shield, Github, Twitter, Linkedin } from 'lucide-react';
import { cn } from '@/lib/utils';

// Map icon names to components
const iconMap = {
  LayoutGrid,
  BookOpen,
  Search,
  BarChart,
  Cloud,
  Server,
  Database,
  Shield
};

const Home = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Navigation
      <header className="fixed w-full top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-gray-100">
        <div className="container-lg py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
              <span className="text-primary font-bold text-xl">N</span>
            </div>
            <span className="font-semibold text-xl gradient-text-primary">{siteConfig.name}</span>
          </div>
          <div className="flex items-center space-x-6">
            <nav className="hidden md:flex items-center space-x-6">
              <a href="#features" className="text-gray-600 hover:text-gray-900 transition-colors">Features</a>
              <a href="#services" className="text-gray-600 hover:text-gray-900 transition-colors">Services</a>
              <a href="#about" className="text-gray-600 hover:text-gray-900 transition-colors">About</a>
            </nav>
            <Link 
              to="/chat" 
              className="btn-primary inline-flex items-center group"
            >
              Get Started
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </header> */}

      {/* Hero section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(139,92,246,0.1),transparent_50%)]"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,rgba(99,102,241,0.1),transparent_50%)]"></div>
        
        {/* Animated background elements */}
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl animate-pulse delay-1000"></div>
        
        <div className="container-lg relative">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-primary/5 border border-primary/10">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
              </span>
              <span className="text-sm font-medium text-primary">AI-Powered Cloud Solutions</span>
            </div>
            
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight gradient-text-primary leading-tight">
              {homePageConfig.hero.title}
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
              {homePageConfig.hero.description}
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link 
                to={homePageConfig.hero.ctaLink} 
                className="btn-primary text-lg px-8 py-4 w-full sm:w-auto"
              >
                {homePageConfig.hero.ctaButton}
              </Link>
              <a 
                href="#demo" 
                className="btn-secondary text-lg px-8 py-4 w-full sm:w-auto"
              >
                Watch Demo
              </a>
            </div>
            
            <div className="pt-8 flex items-center justify-center space-x-8 text-gray-600">
              <div className="flex items-center space-x-2">
                <Shield className="h-5 w-5 text-primary" />
                <span>Enterprise Ready</span>
              </div>
              <div className="flex items-center space-x-2">
                <Cloud className="h-5 w-5 text-primary" />
                <span>Cloud Native</span>
              </div>
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-primary" />
                <span>99.9% Uptime</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Services section */}
      <section id="services" className="py-24 bg-gray-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(139,92,246,0.05),transparent_50%)]"></div>
        
        <div className="container-lg relative">
          <div className="text-center space-y-4 mb-16">
            <span className="inline-block px-4 py-2 rounded-full bg-primary/5 text-primary text-sm font-medium">
              Our Services
            </span>
            <h2 className="text-4xl md:text-5xl font-bold gradient-text-primary">
              Cloud Solutions & Architecture
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Leverage our AI-powered platform to design, implement, and optimize your cloud infrastructure
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {homePageConfig.services.map((service, index) => {
              const IconComponent = iconMap[service.icon as keyof typeof iconMap] || Cloud;
              
              return (
                <div 
                  key={index}
                  className="card hover-lift group"
                >
                  <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
                    <IconComponent className="h-7 w-7 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{service.title}</h3>
                  <p className="text-gray-600 mb-6">{service.description}</p>
                  <a href="#" className="inline-flex items-center text-primary font-medium group-hover:underline">
                    Learn more <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features section */}
      <section id="features" className="py-24">
        <div className="container-lg">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="space-y-8">
              <span className="inline-block px-4 py-2 rounded-full bg-primary/5 text-primary text-sm font-medium">
                AI-Powered Solutions
              </span>
              <h2 className="text-4xl font-bold gradient-text-primary leading-tight">
                Intelligent Cloud Architecture Design
              </h2>
              <p className="text-xl text-gray-600">
                Our AI agents analyze your requirements and automatically generate optimal cloud architecture designs,
                complete with detailed implementation plans, cost estimates, and security recommendations.
              </p>
              
              <ul className="space-y-6">
                {[
                  "AWS, GCP, and Azure cloud diagrams",
                  "Real-time cost optimization",
                  "Security compliance checks",
                  "Multi-region deployment strategies"
                ].map((feature, idx) => (
                  <li key={idx} className="flex items-start">
                    <div className="mr-4 mt-1 bg-primary/10 rounded-full p-1.5">
                      <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>
                    <span className="text-lg">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <div className="pt-4">
                <Link 
                  to="/chat" 
                  className="btn-primary inline-flex items-center text-lg group"
                >
                  Try it now
                  <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            </div>
            
            <div className="relative">
              <div className="card p-8 relative z-10">
                <div className="absolute -top-3 -right-3 px-4 py-2 bg-primary text-white rounded-full text-sm font-medium shadow-lg">
                  AI-Generated
                </div>
                <div className="rounded-xl overflow-hidden shadow-2xl">
                  <img 
                    src="/cloud-architecture-demo.png" 
                    alt="Cloud Architecture" 
                    className="w-full transform hover:scale-105 transition-transform duration-500"
                  />
                </div>
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 font-medium">AWS Multi-region Architecture</span>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                      Cost Optimized
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Decorative elements */}
              <div className="absolute -top-8 -left-8 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl"></div>
              <div className="absolute -bottom-8 -right-8 w-48 h-48 bg-primary/10 rounded-full blur-3xl"></div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gray-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(139,92,246,0.1),transparent_70%)]"></div>
        
        <div className="container-md relative">
          <div className="text-center space-y-8">
            <h2 className="text-4xl md:text-5xl font-bold gradient-text-primary">
              Ready to Transform Your Cloud Infrastructure?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Join thousands of companies using our AI-powered platform to optimize their cloud architecture
            </p>
            <div className="pt-4">
              <Link 
                to="/chat" 
                className="btn-primary inline-flex items-center text-lg px-8 py-4 group"
              >
                Get Started Now
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Enhanced Footer */}
      <footer className="bg-white border-t border-gray-100">
        <div className="container-lg">
          <div className="py-12 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <span className="text-primary font-bold text-xl">N</span>
                </div>
                <span className="font-semibold text-xl gradient-text-primary">{siteConfig.name}</span>
              </div>
              <p className="text-gray-600 mb-6">
                Empowering businesses with intelligent cloud solutions through advanced AI technology.
              </p>
              <div className="flex space-x-4">
                <a href="#" className="text-gray-600 hover:text-primary transition-colors">
                  <Github className="h-6 w-6" />
                </a>
                <a href="#" className="text-gray-600 hover:text-primary transition-colors">
                  <Twitter className="h-6 w-6" />
                </a>
                <a href="#" className="text-gray-600 hover:text-primary transition-colors">
                  <Linkedin className="h-6 w-6" />
                </a>
              </div>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-3">
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Features</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Pricing</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Security</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Enterprise</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-3">
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">About</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Blog</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Careers</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Resources</h4>
              <ul className="space-y-3">
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Documentation</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">API Reference</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Guides</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Support</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-3">
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Privacy</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Terms</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Cookie Policy</a></li>
                <li><a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Licenses</a></li>
              </ul>
            </div>
          </div>
          
          <div className="py-6 border-t border-gray-100 flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-gray-600 text-sm">
              © {new Date().getFullYear()} {siteConfig.name}. All rights reserved.
            </div>
            <div className="flex space-x-6 text-sm">
              <a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Privacy Policy</a>
              <a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Terms of Service</a>
              <a href="#" className="text-gray-600 hover:text-gray-900 transition-colors">Cookie Settings</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;
