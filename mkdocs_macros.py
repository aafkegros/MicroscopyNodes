from pathlib import Path

def define_env(env):
    
    @env.macro
    def youtube(video_id, width=360, height=200):
        return f'''
<div class="yt-lazy" data-id="{video_id}" style="width:{width}px; height:{height}px;">
  <div class="yt-thumbnail" style="background-image: url('https://img.youtube.com/vi/{video_id}/hqdefault.jpg');">
    <div class="yt-play-button"></div>
    <div class="yt-overlay-text">
      Click to load video from YouTube.<br />
      By clicking, you agree to YouTube’s privacy policy.
    </div>
  </div>
</div>
'''

    @env.macro
    def svg(name, css_style='icon'):
        # Adjust path relative to your mkdocs root directory
        full_path = Path(env.project_dir) / "docs" / "html_blender_icons" / f"{name}.svg"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f'<span class="{css_style}">{f.read()}</span>'
        except Exception as e:
            return f"<!-- ERROR loading SVG: {e} -->"

