#! /usr/bin/env python3
"""
I wanted to see multiple layers of selectable folders:
- Folder
  - Subfolder
    - Feature
      * LineString1
      * LineString2
Instead, on import in QGIS, I only get the Features.

If I drag into Google Earth, I actually see the nested folders.
"""


import numpy as np
import simplekml


def main():
    kml = simplekml.Kml()
    top_folder = kml.newfolder(name="Folder")
    sub_folder = top_folder.newfolder(name="Subfolder")
    feature_folder = sub_folder.newfolder(name="Feature")
    lats1 = -90 + np.random.random(5)
    lons1 = 360 * np.random.random(5)
    ls1 = feature_folder.newlinestring(
        name="LineString1", coords=list(zip(lons1, lats1))
    )
    ls1.style.linestyle.color = simplekml.Color.rgb(255, 0, 0, 255)
    lats2 = -90 + np.random.random(5)
    lons2 = 360 * np.random.random(5)
    ls2 = feature_folder.newlinestring(
        name="LineString2", coords=list(zip(lons2, lats2))
    )
    ls2.style.linestyle.color = simplekml.Color.rgb(0, 255, 0, 255)
    kml.save("test_nesting.kml")


if __name__ == "__main__":
    main()
