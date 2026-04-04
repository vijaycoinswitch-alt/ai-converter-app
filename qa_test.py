import os
from jinja2 import Environment, FileSystemLoader

core_tools = [
    'pdf_to_word', 'word_to_pdf', 'pdf_to_excel', 
    'jpg_to_pdf', 'merge_pdf', 'split_pdf', 'compress_pdf'
]

print("="*50)
print("SEO QA AUDIT REPORT DATA")
print("="*50)

# 1. Routes
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        app_py = f.read()
    
    print("\n[ROUTES]")
    for tool in core_tools:
        rt = "/" + tool.replace("_", "-")
        found = "FOUND" if ("@app.route('" + rt + "')" in app_py or '@app.route("' + rt + '")' in app_py) else "MISSING"
        print("Tool {}: {}".format(rt, found))
        
    f_blog = "FOUND" if ('@app.route("/blog")' in app_py or "@app.route('/blog')" in app_py) else "MISSING"
    print("Blog Index (/blog): " + f_blog)
    
    f_post = "FOUND" if ('@app.route("/blog/<slug>")' in app_py or "@app.route('/blog/<slug>')" in app_py) else "MISSING"
    print("Blog Post (/blog/<slug>): " + f_post)
    
    sm_found = "FOUND" if ("@app.route('/sitemap.xml')" in app_py or '@app.route("/sitemap.xml")' in app_py) else "MISSING"
    print("Sitemap (/sitemap.xml): " + sm_found)
    
    rb_found = "FOUND" if ("@app.route('/robots.txt')" in app_py or '@app.route("/robots.txt")' in app_py) else "MISSING"
    print("Robots (/robots.txt): " + rb_found)
    
    # Count blog posts
    blog_posts = app_py.count('"slug":')
    print("Total Blog Posts: " + str(blog_posts))
    
except Exception as e:
    print("Error reading app.py: " + str(e))

# 2. Templates
print("\n[TEMPLATES]")
try:
    env = Environment(loader=FileSystemLoader('templates'))
    for tool in core_tools:
        tpl = 'tools/' + tool + '.html'
        try:
            source, _, _ = env.loader.get_source(env, tpl)
            t = "Y" if "{% block title %}" in source else "N"
            m = "Y" if "{% block meta_description %}" in source else "N"
            h = "Y" if "{% block tool_h1 %}" in source else "N"
            s = "Y" if "{% block seo_content %}" in source else "N"
            f = "Y" if "faq" in source.lower() else "N"
            r = "Y" if "related-tools" in source.lower() else "N"
            sch = "Y" if "schema.org" in source else "N"
            print("/{}: Title[{}] Meta[{}] H1[{}] SEO_Block[{}] FAQ[{}] Related[{}] Schema[{}]".format(tool.replace('_', '-'), t, m, h, s, f, r, sch))
        except Exception as e:
            print(tpl + ": ERROR - " + str(e))
            
    # Check index.html
    source, _, _ = env.loader.get_source(env, 'index.html')
    testi = "Y" if "testimonial" in source.lower() else "N"
    trust = "Y" if "trust-" in source.lower() else "N"
    pop = "Y" if "popular" in source.lower() or "showcase" in source.lower() else "N"
    cta = "Y" if "hero-cta" in source.lower() or "final-cta" in source.lower() else "N"
    print("index.html: Testimonials[{}] Trust[{}] Popular[{}] CTA[{}]".format(testi, trust, pop, cta))
    
    # Check tool_layout.html
    source, _, _ = env.loader.get_source(env, 'tools/tool_layout.html')
    sec = "Y" if ("secure &" in source.lower() or "trust-badge" in source.lower()) else "N"
    print("tool_layout.html: Trust_Badges[{}]".format(sec))
    
    # Check base.html
    source, _, _ = env.loader.get_source(env, 'layouts/base.html')
    can = "Y" if "canonical" in source else "N"
    og = "Y" if "og:" in source else "N"
    font = "Y" if "fonts.googleapis.com" in source else "N"
    print("layouts/base.html: Canonical[{}] OG_Tags[{}] Google_Fonts[{}]".format(can, og, font))

except Exception as e:
    print("Template Error: " + str(e))
    
# 3. CSS
print("\n[CSS]")
css_file = 'static/css/seo_enhancements.css'
if os.path.exists(css_file):
    print("seo_enhancements.css: FOUND ({} bytes)".format(os.path.getsize(css_file)))
else:
    print("seo_enhancements.css: MISSING")
