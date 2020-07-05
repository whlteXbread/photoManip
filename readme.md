# Photo Manipulation Tools

The `photomanip` package has undergone significant refactoring and is in a state of flux.
In general the old code was embarrassing spaghetti code I put together to quickly do something I wanted to do.
Now it's less embarrassing and hopefully more maintainable.

Notes:
* `avg_phoots.py` has been renamed to `photomanip/avg_photos.py` and uses the newly-refactored code and a new CLI interface
* `average_months.py` and `add_date_machine_tags.py` have been deprecated but their functionality has not been fully replaced yet, so they remain in the `deprecated` folder until that time

## Tools
### avg_photos.py

This script will generate an average image (or long exposure simulation) using all the images in a specified folder.
It assumes that the images include metadata about when they were created, and will try to make averages for each day with multiple images, each month with multiple images, and each year with multiple images.

Usage:
```
./avg_phoots.py -i [input_folder] -o [output_folder] -c [combination_method] -t [grouping_tag] -a [author]
```
`input_folder` is any folder you have permission to read that contains `.jpg` files.

`output_folder` is a folder to which you have write permission: all averages will be placed in this folder

`combination_method` is either `crop` or `pad`. `crop` means that all images are cropped into square images with dimensions equal to the smallest dimension found in all the images in the folder. `pad` means that all images are padded into square images with dimensions equal to the largest dimension found in all the images in the folder. Default is `crop`.

`grouping_tag` is a prefix to an IPTC keyword that contains a date in YYYYMMDD format, for example with the keyword `mydate=19991231`, the grouping tag would be `mydate=`. this can be used to group photos instead of the EXIF `DateTimeCreated` if desired. Default is `None`.

`author` is the author generating the average image. Default is `andrew catellier`, in case you want to give me credit for creating your average images.

`flickr_set_id` is a valid Flickr photoset ID to which you have upload permissions. If set, the program will attempt to upload daily averages to flickr using a key and secret specified in `config.yaml`:

```
flickr:
  key:
    '[FLICKR_KEY]'
  secret:
    '[FLICKR_SECRET]'
```

`cache` is boolean, specifying whether the program should keep track of intermediate average results. This cache can significantly reduce processing time if one is repeatedly generating averages from one set of images but can also take a significant amount of space—the cache images are M x N x 3 32 bit float TIFs.

## Deprecated Tools
### average_months.py
The idea behind this script is to download all the photos from a Flickr set specified by its set ID, organize them by month taken, and then generate one average image (or long exposure simulation) for each month. It leverages `avg_phoots.py` to do the photo manipulation.

Usage:
```
    ./average_months.py [flickr_set_id]
```

### add_date_machine_tags.py

This script will add machine tags to all photos in a specified flickr set with a specified namespace and predicate, but the value will be calculated based on the title (or, if you uncomment a line of code and comment a couple others, the photo's "taken" date). A valid OAuth key with write permissions must be available.

Usage:
```
    ./add_date_machine_tags.py [set_id] [namespace] [predicate]
```
