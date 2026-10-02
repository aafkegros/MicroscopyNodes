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
