import win32com.client
import os
import sys
import tempfile

def create_native_animation():
    try:
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        prs = ppt.Presentations.Add()
        slide = prs.Slides.Add(1, 1) # Title slide type
        
        shape1 = slide.Shapes.AddTextbox(1, 100, 100, 300, 50)
        shape1.TextFrame.TextRange.Text = "Shape 1"
        eff1 = slide.TimeLine.MainSequence.AddEffect(shape1, 10) 
        eff1.Timing.TriggerType = 3 # AfterPrev
        
        shape2 = slide.Shapes.AddTextbox(1, 100, 200, 300, 50)
        shape2.TextFrame.TextRange.Text = "Shape 2"
        eff2 = slide.TimeLine.MainSequence.AddEffect(shape2, 10) 
        eff2.Timing.TriggerType = 3 # AfterPrev
        
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, "native_auto_animated.pptx")
        
        if os.path.exists(out_path):
            os.remove(out_path)
            
        prs.SaveAs(out_path)
        prs.Close()
        ppt.Quit()
        
        print(f"Created native auto animated pptx at: {out_path}")
    except Exception as e:
        print(f"Failed to create native animation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_native_animation()
