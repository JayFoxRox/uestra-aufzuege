#!/usr/bin/env python3

import json
from bs4 import BeautifulSoup

def getAufzuegeUestraDe():
    import requests
    response = requests.get("https://aufzuege.uestra.de/ApplianceStatus", params={
        "mode": 3
    })
    return response

def parseAufzuegeUestraDe(content):
    data = []

    soup = BeautifulSoup(content, features="html.parser")
    #open("/tmp/uestra.html", "w").write(soup.prettify())

    #<div class="panel-group" id="accordion" role="tablist" aria-multiselectable="true">
    panelGroups = soup.find_all("div", {'class': 'panel-group'})
    assert(len(panelGroups) == 1)
    panelGroup = panelGroups[0]
    
    #<div class="panel panel-default allstations broken">
    panels = panelGroup.select("div.panel.allstations")
    for panel in panels:

        titles = panel.find_all("h3", {'class': 'panel-title'})
        #print("\n"*100)
        #print(panel, titles)
        assert(len(titles) == 1)
        title = titles[0]

        station = {
            'title': title.text.strip(),
            'escalators': [],
            'elevators': []
        }

        stationInfos = panel.find_all("p", {'class': 'stationInfo'})
        assert(len(stationInfos) == 1)
        stationInfo = stationInfos[0]
        spans = stationInfo.find_all("span")
        for span in spans:
            strongs = span.find_all("strong")

            if len(strongs) == 0:
                if span.text == "außer Betrieb.":
                    continue

            assert(len(strongs) == 1)
            strong = strongs[0]

            count, total = [int(x.strip()) for x in strong.text.split("/")]
            
            textAfter = strong.next_sibling
            if textAfter == " Aufzügen":
                pass # station['elevatorCount'] = [count, total]
            elif textAfter == " Rolltreppen":
                pass # station['escalatorCount'] = [count, total]
            else:
                print(f"Unknown '{textAfter}'")
            
            #<p class="stationInfo">
            #<span>Derzeit sind <strong>0 / 1</strong> Aufzügen</span>
            #<span>und <strong>1 / 16</strong> Rolltreppen</span>
            #<span>außer Betrieb.</span>
            #</p>
                
        movements = panel.find_all("div", class_="lines")
        for movement in movements:
            
            # Skip empty elements
            if "emptylines" in movement['class']:
                continue

            uls = movement.find_all("ul", class_='linesList')
            assert(len(uls) == 1)
            ul = uls[0]

            lis = ul.find_all("li")
            levels = []
            for li in lis:

                # Get title
                layerContentBoxes = li.find_all("div", class_="layerContentBox")
                assert(len(layerContentBoxes) == 1)
                layerContentBox = layerContentBoxes[0]
                titleDiv = layerContentBox.find_next("div")
                assert('class' not in titleDiv)
                title = titleDiv.text

                # Check for linenumbers
                lines = []
                lineNumberDivs = li.find_all("div", class_="lineNumbers")
                for lineNumberDiv in lineNumberDivs:
                    direction = lineNumberDiv.find_next_sibling()
                    groupedLineNumberDivs = lineNumberDiv.find_all("div")    
                    for groupedLineNumberDiv in groupedLineNumberDivs:
                        #print(groupedLineNumberDiv['class'], direction.text.strip())
                        lineNumber = int(groupedLineNumberDiv['class'][0].replace("_", "").strip())
                        lines += [{
                            "number": lineNumber,
                            'heading': direction.text.strip()
                        }]

                classes = li.get('class', [])
                passed = 'passed' in classes

                levels += [{
                    'title': title,
                    'passed': passed,
                    'lines': lines
                }]

            pictos = movement.find_all("img") # class is one of "pictoEs" / "pictoEl"
            assert(len(pictos) == 1)
            picto = pictos[0]

            pictoSrc = picto['src']
            extras = {}
            if pictoSrc == "/Content/Aufzug.png":
                category = "elevators"
            elif pictoSrc == "/Content/TreppeRunter.png":
                category = 'escalators'
                extras = {
                    'direction': 'down'
                }
            elif pictoSrc == "/Content/TreppeRaufRunter.png":
                category = 'escalators'
                extras = {
                    'direction': 'switching'
                }
            elif pictoSrc == "/Content/TreppeRauf.png":
                category = 'escalators'
                extras = {
                    'direction': 'up'
                }
                pass
            else:
                print(f"unable to match '{pictoSrc}'")
                assert(False)

            actBtns = movement.find_all("div", class_="actBtn")
            assert(len(actBtns) == 1)
            actBtn = actBtns[0]
            id = actBtn.text.strip()

            alertDivs = movement.find_all("div", class_="alert")
            if len(alertDivs) == 0:
                alert = False
            else:
                assert(len(alertDivs) == 1)
                alertDiv = alertDivs[0]
                for elem in alertDiv.find_all(["br"]):
                    elem.append('\n')
                alert = alertDiv.text.strip()

            station[category] += [{
                'id': id,
                'alert': alert,
                'levels': levels
            } | extras]
                    
        data += [station]
    
    #FIXME: Apply some manual fixes:
    # - Sr.76 goes to "Verteilerebene West"
    # - Kr.62C is overly specific "Bahnsteig 1,2,8,18" should be "Bahnsteigebene"
    
    return data

if __name__ == "__main__":
    print("Getting aufzuege.uestra.de")
    response = getAufzuegeUestraDe()
    assert(response.status_code == 200)

    print("Parsing aufzuege.uestra.de")
    data = parseAufzuegeUestraDe(response.content)

    jsonData = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)
    print(jsonData)
    if False:
        open("/tmp/uestra.json", "w").write(jsonData)