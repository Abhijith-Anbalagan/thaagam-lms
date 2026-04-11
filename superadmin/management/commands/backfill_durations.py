"""
Management command to backfill duration_seconds for all existing videos.

Usage:
    python manage.py backfill_durations
"""
import os
import struct
import tempfile

from django.core.management.base import BaseCommand
from superadmin.models import GlobalConceptVideo, GlobalCourse


def get_duration_from_file(file_field):
    """Extract duration in seconds from a FileField using MP4 atom parsing."""
    if not file_field:
        return 0
    try:
        # Read file content
        file_field.open('rb')
        data = file_field.read()
        file_field.close()

        # Try mutagen first
        try:
            import tempfile, os
            suffix = os.path.splitext(file_field.name)[1] or '.mp4'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(data)
            tmp.close()
            from mutagen import File as MutagenFile
            af = MutagenFile(tmp.name)
            os.unlink(tmp.name)
            if af and af.info:
                return int(af.info.length)
        except Exception:
            pass

        # Fallback: parse MP4 mvhd atom
        i = 0
        while i < len(data) - 8:
            size = struct.unpack('>I', data[i:i+4])[0]
            name = data[i+4:i+8]
            if name == b'mvhd':
                version = data[i+8]
                if version == 1:
                    time_scale = struct.unpack('>I', data[i+28:i+32])[0]
                    duration   = struct.unpack('>Q', data[i+32:i+40])[0]
                else:
                    time_scale = struct.unpack('>I', data[i+20:i+24])[0]
                    duration   = struct.unpack('>I', data[i+24:i+28])[0]
                if time_scale > 0:
                    return int(duration / time_scale)
            if size < 8:
                break
            i += size
    except Exception:
        pass
    return 0


class Command(BaseCommand):
    help = 'Backfill duration_seconds for all existing uploaded videos'

    def handle(self, *args, **options):
        videos = GlobalConceptVideo.objects.filter(file__isnull=False, duration_seconds=0).exclude(file='')
        total  = videos.count()
        self.stdout.write(f'Found {total} videos with duration_seconds=0')

        updated = 0
        for video in videos:
            dur = get_duration_from_file(video.file)
            if dur > 0:
                video.duration_seconds = dur
                video.save(update_fields=['duration_seconds'])
                updated += 1
                self.stdout.write(f'  ✓ [{video.pk}] {video.title or "Untitled"} → {dur}s')
            else:
                self.stdout.write(f'  ✗ [{video.pk}] {video.title or "Untitled"} → could not read duration')

        # Sync total_hours for all courses
        courses_updated = 0
        for course in GlobalCourse.objects.all():
            old = course.total_hours
            course.sync_total_hours()
            if course.total_hours != old:
                courses_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Updated {updated}/{total} videos. '
            f'Synced total_hours for {courses_updated} courses.'
        ))
