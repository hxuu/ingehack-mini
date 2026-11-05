#!/usr/bin/env python3

import base64
import ctypes
import gzip
import hashlib
import hmac
import os
import platform
import sys


KEY = '2d37933c18d5b02b6093cc9cfcd7899c18b4fe1fc4c7a29a9371d7b6a86ccd1f'
NONCE = '656e44987683a0871ec6d9bd83ad58c5'
TAG = 'acdc5a91e624c5172884b3745093c7d676f930f687cd607bfecf51ec87a2cbe0'
PAYLOAD = (
    '1L5vGgz8YrmhRTlR536PmTWi7F6cV2YcHxCLNWtuzd7B63lGO83pz+3SrXb/+HEPB+ZNBy9xPdT9'
    'JYD9X/hN5uGzp5lp7d8/NjmVnv+pmXAoNeyXcyiAUEpC6gnjtS5H98PEdJ36EcAwT7D5KMNNViSr'
    'le8kpuLKKQFeo7Gdh9oSu0SL+oEXiFO1G3vLxlyqKntg8OZIIQZ09fMiF+OZeU3+NjlQs0KoX3At'
    '2KbIocspyYvUyFeGcNk2aLVVuJrm/kY7OxgGPsEEdlHKxrBIfmSV4xqA0qgE6ET8XLlYUA0YlXKd'
    'eia7i1QoknomDgBUqAFvbf87M1M9Wa/UhX8XZE6IEjE43rhEUYMzJ1bGMWPWDbfkBTMYZX4U3Yri'
    '+2h9lWO687Ny5uPkXGs1hY8rpukRqZViRRxcuxljdI+VTDpHU7kCAPHPRDAtzVw+sIlWQGJOL+d+'
    'sKEpHINaByK4XcGX0mNXyI9VKhnf9/AsFXhEhc6sKIKs8aWlOB/Tby0MX2O1WGYxLMREsiE59Ee8'
    'fH5uEkm1EOsc9gY/Y2hnVBff96lMWt2/geumxcFyCMiYgq72jsBuX0NBvFTRsCtDcx+850sh6Wbk'
    'ETs60ZlnJ82UVZqQZ38knvlwhsrL9aiKEF+5y+3yEjLF029o+w3OGWP+1+qZ9OhCfSwqXKuZxFoH'
    'GSt93bWd6V+aun+qmDpK/CIHpVJ94E9WUN8TW7AxT5jINwMk0koMkMkGJSZB18l6EGnFWMds2hKZ'
    'exrw3KKj/KIQLAZxTz73mz+ykFNmjzBLlztxiG0SW3TKlMbyYJJYU0PR5B8mW/YG1OJjf8xa+Zgt'
    'Fiw+Ixcfol2vUHdNdctvj9MDr3agGoRfH7NRAVlIRd/U45I0PO+H+yAwU6dU6zYMs+ejWllUF8wN'
    'Gw2+2XRtIUZ7LlNv0rCLyn3WUqDar+QikFoKvn1U4mkCDaI3gkeI9bV7DyoMR3ZpWa03EqrOSGj7'
    'mdJk//gna2WRC61XAcISaMCTMn/SdaSwCPSOiy/FNg0n6pkuuBTNsJcddnIjJ8kqvkjbvuw08qtc'
    'JZmRXYI6g9Am8KXky0/NvD6/ILVYLu9RIeK+basu6YDFNlxs+sQXNSfsw6lsSIcUjUxgKw3Bm6xa'
    'zSVcEy0o96LKP9QyT69QnMRu7NlU3/jBv1S6qoQ9tRhYs076YUJDIb6rmUntCrmJ20fLhgsi4Ofq'
    'P59OeyDJIbq0PEebR0CovGrbDP8Ez5x8QsGKSDDMxwm+VQI13jFbJZ/lkD2kHt5BbBI55Lw7WXms'
    'UmbwKwPjYhiB9t0XSu5fW2d72jOmOBq27VSe9O1CkzcJ+DiOyXmqz4lN7GRlGWT0/MPwrSPKNDTn'
    'ux1jC26FSgtcNePQd6xCekHkNwdVUZPhgYDGq5mOYi177tXohHtNcJimM7cZhTu45cmbeoCP5maB'
    'Bxf6NN8kF4x4mHZ+VTFwaJR9qmCOnWzybmeLCF9qvEgOLnr4JkptRio1NiL6+n+hHs8+cg6a34PP'
    '+CKdiafa9XFRVZKN/EPpk/YTqfU384KNbrduDY8pqw8GsbDrCc9FcBxe04hd3+07RwkP85l4b3FC'
    '+4PUP3fpzZGPXOBkQWJFed2eOW/6RoK5rXzxPvdmK/2Hdmt1IUhlDYy+kjCQ0TuHA19f1ZawcZ4B'
    '0AAWgAMZ2tAaEz0UbMGkJTX1lAJBppHIjgyPp27sc/S6l9rLn0FlBj9Y4OG0bGYdvLjS8ioiZRZT'
    'J5Pw1ANE0yUU2YbZslknRXrUQZWwAP9siqAX+SUKbBhObyCeUnKAy195iQNm1RUM53wTHqBBasrM'
    'ClRAx457UkaT+dgPKcCPxtxrAn6Pr5TG629Fsh19kKyvGh0KgVrxnNCPNKRS95e48PWUmC0V1Q5T'
    'WmDvVV0hoNssK2hPDbqwNidGm4K0t6dOdAC+tK1PvU//N4aZpjPIjI3+f/Nzbdp0kuiJJDpWHMKw'
    'bYGXJuVN++GHeRkh0CJszngnpGagLEo5VbwE9mS1HVS7GtNiVDlAf6lyYJTJytzhhqVWhbFOFhhg'
    '/Jy+YIuzY3S5rpZE7lpfCmJhdcSWdqnkVD9Ab7TWMISyFn1iFyNHPzs45GE9IEejBjj/bc7nc4Nh'
    'tHoz8Nup6wyznBifWnmABvlco3KspiHMY5hWUJ9YID5eLhDuMGiY8PV+ZWTcO8vga5cdHJPtM5/O'
    'e4RAddtbsmjYh1ip/kZfQMaUaMjiuDD8yx954LSGbZxSQuP05bv+PIjlvmqT5f2YJEMLy4B/eoVh'
    'JvnGt6k9eoUKys4r9yGbLlp5nAd9xUKW/EuN10F/zX4cUjLIYb+ZsB8OIxHM4UPgGLv7/eT5/Co9'
    '/cAGKZTtqMHmB+1caaZN2RSc3/0HPZFPuJhEQSBBzN6PTbWa/67Et6P7bAzrIk1k/tvsWOEg5cDn'
    'NeuV8iUTwTT074FgrmtUnO+npew69050KnncTC1WNdz2H15x/ZuALgQRkwD1wGZph99Np129Wjd4'
    'HtX3lUF5/1WSTwWxaV4RA0tob7bZN4BcfQcp1phUVP9Aqou3UtkLr4lhYJyM7fORmI+iXdulLwDK'
    'aKykEdql5Idwi9LVe1DdIOJn0Ab7KkqJ7RM8IqqsaElx7+ZzVPZDLQK8cWQ00K7ROFAxyORUFYbV'
    '9+wEr1hHE61k0F8xdal3r+sAnnmGljBsv/4XvsOS/1xzLQCGfyI8GNZYJHuCuXp7d8yaZZzmYSTe'
    'suZ6EXnGJueJmJx2gr5xRELqejLNCiSiXZe+ajCIm4BOuUwcKZPyHn8OErY/tlForEhX3lhZR4xX'
    'nyPkNgaD+zGQtX/SbTy5nUYWf1RQOHNycmWxcoNsVWHUlVUZct8Me0oGEElWdr0q80EUSSvWgvV1'
    'DhPl52YVGgGD1Ev3YOoRUJfHW+V2deLrRjz8Mig6qIJFhK1o3VRmznly7WmpYiWl52hw6mTONoxr'
    'JhZFpzI9rWjYT9rQgnri5LZApokUQ9NGTm2Uu7OWbJRbKveyKmzPvouv1BhkJCFhZjLjUhlvqtlL'
    'GeC4MTdNU45IHthTMD2ZwEr9m6QZtS08/oHKNzCu4+Us2pVn8Y6GKYwuJR3BPld165jbqV5uImvg'
    'i60vhGq5nmc+SxuHfLnLfbHvPuIU32+n3n2XrLIsWEIilZL8fCvp2Se5bhkQCJ76W3aC93VW1c7M'
    'ka5awdDJW/Y2AsC338vcxJGHGGnAuqnrlv16ioz7njvO6xDuAl9Op9h4xGlTUntk0dUktMegN64I'
    'VtnlRPAkLDUFdA1Ino8xRU3sHPu6cq8yISZyOtvCKUWV3gZ430y0yx4N3zpVlyD8ToKNskYnK/DD'
    'yl9ffeoIAfYc2+HGTx904gu2QW26anG+K7Pb+T/vrSBJVjMlMu8f4a0/HUKCeqimKl1rdcWPZy3O'
    '8NdHUXK5tmWlseBq0sWQp38tUlJvEHmhLCX3ufZfau0GuaMCaI2vg09EvG85DfMMFdy9BXThqc93'
    'N+EmX7SUIJ0detfvuh4lLwNa2S3HCZ4qr8r2+CXnKaqJFf/FZGWkO086snizT1ZWUHyYi9xbnuCK'
    'wA0PQqLAk0Du6cs4CEGsFoYta6FBNE/ie98MBU9r06zI6ir8BDS/uc3VWLJsxKXCwt10uyVq2TIy'
    'AmXSips/EPUon0JxEJ4DnGEM0XkZ1/oCZudkYNfeqHVH9UqGlVZTf3QfP59EIMcS8GhgJmQ+6qmp'
    'eb7h/KUjAmz7/nd09cjOfp894wPUbB0c1i9JurB/sgblBVBqnDv0O13rmhPKuB+LgiQ/9FaReFL6'
    'P4vcPhAJAxFg8x3NlG613IaBYwAW52/DnPS5Xjbq50is/1QQ9HSQU8Ep/UVHxkBRqS3cdbWKrxhV'
    'kkFJza9iYeqgZ0Z+oIKGF5023Kh/q1LoeoQMrCtJKB80mNVeXB5IlPoOOsIbIKg7kZBqcKBu5sqV'
    'mf9/kBwpFh/zN5RFIKs75yptY0AnP6tdKzAIwQbrWE/mPT3ZIl15RePLkGYouA=='
)


def unpack():
    key = bytes.fromhex(KEY)
    nonce = bytes.fromhex(NONCE)
    encrypted = base64.b64decode(PAYLOAD, validate=True)
    actual = hmac.new(key, nonce + encrypted, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(TAG, actual):
        raise ValueError("damaged payload")
    clear = bytearray()
    for offset in range(0, len(encrypted), 32):
        counter = (offset // 32).to_bytes(4, "little")
        stream = hashlib.sha256(key + nonce + counter).digest()
        clear.extend(a ^ b for a, b in zip(encrypted[offset:offset + 32], stream))
    return gzip.decompress(clear)


def main():
    if len(sys.argv) != 2:
        print("usage: python3 stub.py 'ingehack{candidate}'", file=sys.stderr)
        return 2
    token = sys.argv[1]
    if token.startswith("ingehack{") and token.endswith("}"):
        token = token[9:-1]
    try:
        token = token.encode("ascii")
    except UnicodeEncodeError:
        print("false")
        return 1
    if len(token) != 57:
        print("false")
        return 1
    if (sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64")
            or ctypes.sizeof(ctypes.c_void_p) != 8):
        print("requires x86-64 Linux and 64-bit Python 3.9+", file=sys.stderr)
        return 2

    fd = os.memfd_create("stub-offline", flags=0)
    try:
        with os.fdopen(fd, "wb", closefd=False) as target:
            target.write(unpack())
        library = ctypes.CDLL("/proc/self/fd/" + str(fd))
        cuts = (0, 9, 18, 23, 39, 45, 57)
        passed = True
        for i in range(6):
            check = getattr(library, "check" + str(i + 1))
            check.argtypes = (ctypes.c_char_p, ctypes.c_size_t)
            check.restype = ctypes.c_int
            part = token[cuts[i]:cuts[i + 1]]
            passed &= check(part, len(part)) == 1
    finally:
        os.close(fd)
    if passed:
        print("ingehack{" + token.decode("ascii") + "}")
        return 0
    print("false")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
