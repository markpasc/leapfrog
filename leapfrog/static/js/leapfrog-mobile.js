
Ext.setup({

    onReady: function () {

        var windowSize = 10;
        var loadThreshold = 2;
        var loadAhead = 4;
        var earliestTime = null;
        var latestTime = null;
        var currentIndex = 0;
        var loadDirection = 0;
        var loadedItems = {};

        var loadItems = function (numItems, extraParams, callback) {
            Ext.Ajax.request({
                url: '/stream.json?html=1&limit='+numItems+'&'+extraParams,
                timeout: 3000,
                method: 'GET',
                success: function(xhr) {
                    var data = Ext.util.JSON.decode(xhr.responseText);
                    callback(data);
                }
            });
        };

        var loaderMaker = function (myDirection) {
            return function () {
                if (loadDirection != myDirection) {
                    console.log("Starting to load data to move in the direction "+myDirection);
                    loadDirection = myDirection;
                    var extraParams;

                    if (myDirection == 1) {
                        extraParams = 'before='+escape(earliestTime);
                    }
                    else {
                        extraParams = 'after='+escape(latestTime);
                    }

                    loadItems(loadAhead, extraParams, function (data) {
                        if (loadDirection != myDirection) {
                            // This is no longer the direction we're trying to go,
                            // so ignore the response altogether.
                            return;
                        }
                        loadDirection = 0;

                        var items = data.items;
                        var numItems = items.length;
                        console.log("Got "+numItems+" items for direction "+myDirection);
                        if (numItems == 0) return;

                        for (var i = 0; i < numItems; i++) {
                            var item = items[i];
                            if (loadedItems[item.id]) continue;
                            var itemPanel = panelForItem(item);
                            registerLoadedItem(item);
                            if (myDirection == 1) {
                                carousel.items.addAll([ itemPanel ]);
                                registerLoadedItem(item);
                                // Remove the item from the front
                                // to keep the window size constant.
                                var first = carousel.items.first();
                                registerUnloadedItem(first.leapId);
                                carousel.items.remove(first);
                            }
                            else {
                                carousel.items.insert(i, itemPanel);
                                var last = carousel.items.last();
                                registerUnloadedItem(last.leapId);
                                carousel.items.remove(last);
                            }
                        }
                        earliestTime = carousel.items.last().leapTime;
                        latestTime = carousel.items.first().leapTime;
                        var oldIndex = currentIndex;
                        currentIndex = carousel.getActiveIndex();
                        console.log("Index reset from "+oldIndex+" to "+currentIndex);

                        carousel.doLayout();
                    });
                }
            };
        };

        var loadOlder = loaderMaker(1);
        var loadNewer = loaderMaker(-1);

        var carousel = new Ext.Carousel({
            fullscreen: true,
            ui: "light",
            items: [],
            indicator: false
        });

        var onCardSwitch = function () {
            var newIndex = carousel.getActiveIndex();
            var direction = newIndex - currentIndex;

            console.log("Direction is " + direction + " moving from " + currentIndex + " to " + newIndex);

            if (direction > 0) {
                // Browsing right, back in time
                if (newIndex >= windowSize - loadThreshold) {
                    loadOlder();
                }
            }
            else if (direction < 0) {
                // Browsing right, forwards in time
                if (newIndex <= loadThreshold) {
                    loadNewer();
                }
            }

            currentIndex = newIndex;
        };

        var registerLoadedItem = function (item) {
            loadedItems[item.id] = item.time;
        };
        var registerUnloadedItem = function (itemId) {
            delete loadedItems[itemId];
        };
        var panelForItem = function (item) {
            html = "<div class=\"itemholder\">"+item.html+"</div>";
            var itemPanel = new Ext.Panel({
                html: html,
                scroll: true
            });
            itemPanel.leapId = item.id;
            itemPanel.leapTime = item.time;
            return itemPanel;
        };

        loadItems(windowSize, '', function (data) {
            if (! data) return;

            carousel.items.clear();
            var itemPanels = [];
            var items = data.items;
            var numItems = items.length;
            for (var i = 0; i < numItems; i++) {
                var item = items[i];
                var itemPanel = panelForItem(item);
                itemPanels.push(itemPanel);
                registerLoadedItem(item);
            }
            if (numItems > 0) {
                latestTime = items[0].time;
                earliestTime = items[numItems - 1].time;
            }
            carousel.items.addAll(itemPanels);
            carousel.doLayout();
            // We delay installing this until the first bunch
            // of items is loaded so we don't start issuing
            // followup requests before we have any data.
            carousel.on("cardswitch", onCardSwitch);
        });

    }

});
