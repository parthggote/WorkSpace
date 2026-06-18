'use client';

import React from 'react';
import Link from 'next/link';
import { Menu, X, ChevronRight, ArrowRight, Zap, Database, Shield, Star, Layers } from 'lucide-react';

export default function HeroSection() {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement | null>(null);

  // Close on ESC & click outside (mobile overlay)
  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setMenuOpen(false);
    }
    function onClickOutside(e: MouseEvent) {
      if (!menuRef.current) return;
      if (menuRef.current.contains(e.target as Node)) return;
      setMenuOpen(false);
    }

    if (menuOpen) {
      document.addEventListener('keydown', onKey);
      document.addEventListener('click', onClickOutside);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('click', onClickOutside);
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  return (
    <>
      <section className="relative w-full flex flex-col items-center pb-44 min-h-screen bg-background dark:bg-background text-foreground text-sm overflow-hidden">
        {/* Yellow/Golden hue glow behind the text */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-yellow-500/10 md:bg-yellow-500/15 rounded-full blur-[100px] pointer-events-none"></div>
        
        {/* Subtle grid background effect using CSS */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>

        <nav className="relative z-10 flex items-center justify-between p-4 md:px-16 lg:px-24 xl:px-32 md:py-6 w-full">
          <Link href="/" aria-label="Workspace home" className="flex items-center gap-3">
            <img src="/logo.svg" alt="Workspace Logo" className="w-8 h-8 object-contain" />
            <span className="font-bold text-xl tracking-tight">Workspace</span>
          </Link>

          <div
            id="menu"
            ref={menuRef}
            className={[
              'max-md:absolute max-md:top-0 max-md:left-0 max-md:transition-all max-md:duration-300 max-md:overflow-hidden max-md:h-screen max-md:bg-background/95 max-md:backdrop-blur-md',
              'flex items-center gap-8 font-medium',
              'max-md:flex-col max-md:justify-center max-md:border-r max-md:border-border/50',
              menuOpen ? 'max-md:w-64 max-md:shadow-2xl' : 'max-md:w-0',
            ].join(' ')}
            aria-hidden={!menuOpen}
          >
            <a href="#capabilities" className="hover:text-muted-foreground transition-colors flex items-center gap-2">
              <Layers className="w-4 h-4" /> Capabilities
            </a>
            <a href="#features" className="hover:text-muted-foreground transition-colors flex items-center gap-2">
              <Star className="w-4 h-4" /> Features
            </a>

            <button
              onClick={() => setMenuOpen(false)}
              className="md:hidden bg-muted hover:bg-muted/80 text-foreground p-2 rounded-md aspect-square font-medium transition absolute top-4 right-4"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="hidden md:flex items-center gap-4">
            <Link href="/login">
              <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2.5 rounded-full font-medium transition shadow-sm hover:shadow-md">
                Login / Sign Up
              </button>
            </Link>
          </div>

          <button
            id="open-menu"
            onClick={() => setMenuOpen(true)}
            className="md:hidden bg-primary/10 hover:bg-primary/20 text-primary p-2 rounded-md aspect-square font-medium transition"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        </nav>

        <a 
          href="#features" 
          className="relative z-10 flex items-center gap-2 border border-border/50 hover:border-border bg-background/50 backdrop-blur-sm rounded-full w-max mx-auto px-4 py-1.5 mt-20 md:mt-16 text-sm transition-all hover:bg-muted/30"
        >
          <span className="text-muted-foreground font-medium">Check out features</span>
          <div className="flex items-center gap-1 font-semibold text-primary">
            <span>Read more</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </a>

        <h1 className="relative z-10 text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight max-w-[900px] text-center mx-auto mt-8 leading-tight">
          Intelligent context-aware reasoning for your entire workflow
        </h1>

        <p className="relative z-10 text-base md:text-lg text-muted-foreground mx-auto max-w-2xl text-center mt-6 max-md:px-4 leading-relaxed">
          Streamline your research and coding process with persistent context and seamless automation. Build sleek, consistent workflows without wrestling with boilerplate.
        </p>

        <div className="relative z-10 mx-auto w-full flex flex-col sm:flex-row items-center justify-center gap-4 mt-10 px-4">
          <Link href="/login" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-3.5 rounded-full font-medium transition shadow-lg hover:shadow-xl flex items-center justify-center gap-2">
              Get Started for Free <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>
      </section>

      <section id="capabilities" className="w-full bg-muted/30 py-24 px-4 md:px-16 lg:px-24">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-12">Our Capabilities</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-8 bg-card rounded-2xl shadow-sm border border-border flex flex-col items-center">
              <Zap className="w-10 h-10 text-primary mb-6" />
              <h3 className="font-bold text-xl mb-3">Agentic Framework</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">Powered by stateful multi-agent architectures for robust, autonomous execution of complex tasks.</p>
            </div>
            <div className="p-8 bg-card rounded-2xl shadow-sm border border-border flex flex-col items-center">
              <Database className="w-10 h-10 text-primary mb-6" />
              <h3 className="font-bold text-xl mb-3">Cross-Chat Memory</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">Persistent vector retrieval ensures the agent never forgets past contexts, code snippets, or decisions.</p>
            </div>
            <div className="p-8 bg-card rounded-2xl shadow-sm border border-border flex flex-col items-center">
              <Shield className="w-10 h-10 text-primary mb-6" />
              <h3 className="font-bold text-xl mb-3">Code Generation</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">Seamlessly draft, review, and iterate on entire codebases with intelligent context awareness.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="w-full bg-background py-24 px-4 md:px-16 lg:px-24">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-12">Core Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left">
            <div className="p-8 border border-border rounded-2xl hover:border-primary/50 transition-colors">
              <h3 className="font-bold text-lg mb-2">Live Web Connectivity</h3>
              <p className="text-muted-foreground text-sm">Instantly retrieve live data, documentation, and search results to ground LLM reasoning in reality.</p>
            </div>
            <div className="p-8 border border-border rounded-2xl hover:border-primary/50 transition-colors">
              <h3 className="font-bold text-lg mb-2">Real-time Streaming</h3>
              <p className="text-muted-foreground text-sm">Experience ultra-low latency token streaming and watch the agent's thought process unfold in real-time.</p>
            </div>
            <div className="p-8 border border-border rounded-2xl hover:border-primary/50 transition-colors">
              <h3 className="font-bold text-lg mb-2">Secure Authentication</h3>
              <p className="text-muted-foreground text-sm">Enterprise-grade security using Supabase SSO and strict Row Level Security for data isolation.</p>
            </div>
            <div className="p-8 border border-border rounded-2xl hover:border-primary/50 transition-colors">
              <h3 className="font-bold text-lg mb-2">Cost Management</h3>
              <p className="text-muted-foreground text-sm">Intelligent model routing via OpenRouter ensures maximum performance while enforcing strict API cost caps.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
