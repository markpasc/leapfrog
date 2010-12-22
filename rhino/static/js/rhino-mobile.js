
Ext.setup({

    onReady: function () {

        var loadItems = function (callback) {
            Ext.Ajax.request({
                url: '/stream.json?html=1',
                timeout: 3000,
                method: 'GET',
                success: function(xhr) {
                    data = Ext.util.JSON.decode(xhr.responseText);
                    callback(data);
                }
            });
        };

        var carousel = new Ext.Carousel({
            fullscreen: true,
            ui: "light",
            items: [],
            indicator: false,
        });

        loadItems(function (data) {
            if (! data) return;

            carousel.items.clear();
            itemPanels = [];
            items = data.items;
            var numItems = items.length;
            for (var i = 0; i < numItems; i++) {
                item = items[i];
                html = "<div class=\"itemholder\">"+item.html+"</div>";
                var itemPanel = new Ext.Panel({
                    html: html,
                });
                itemPanels.push(itemPanel);
            }
            carousel.items.addAll(itemPanels);
            carousel.doLayout();
        });

    }

});
